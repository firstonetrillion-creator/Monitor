using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;

namespace CerradoAbertoLauncher
{
    internal static class Program
    {
        private const int PgPort = 55432;
        private const int ApiPort = 8000;
        private const int WebPort = 3000;

        private static readonly object ShutdownLock = new object();
        private static bool _shuttingDown;
        private static string _repoRoot = "";
        private static string _pgCtlPath = "";
        private static string _pgDataDir = "";
        private static bool _pgStartedByUs;
        private static Process _apiProcess;
        private static Process _webProcess;
        private static ConsoleCtrlDelegate _ctrlHandler;

        private delegate bool ConsoleCtrlDelegate(int ctrlType);

        [DllImport("kernel32.dll")]
        private static extern bool SetConsoleCtrlHandler(ConsoleCtrlDelegate handler, bool add);

        private static int Main(string[] args)
        {
            Console.OutputEncoding = Encoding.UTF8;
            Console.Title = "Cerrado Aberto — Servidor Local (Inhumas/GO)";

            bool noBrowser = false;
            foreach (string arg in args)
            {
                if (string.Equals(arg, "--no-browser", StringComparison.OrdinalIgnoreCase))
                {
                    noBrowser = true;
                }
            }

            _ctrlHandler = OnConsoleCtrl;
            SetConsoleCtrlHandler(_ctrlHandler, true);

            try
            {
                PrintBanner();

                _repoRoot = FindRepoRoot();
                if (string.IsNullOrEmpty(_repoRoot))
                {
                    FailAndWait(
                        "Nao foi possivel localizar a raiz do repositorio (pastas apps\\api e apps\\web).\n" +
                        "Coloque o CerradoAberto.exe na pasta raiz do projeto.");
                    return 1;
                }

                Console.WriteLine("[1/4] Repositorio encontrado em: " + _repoRoot);

                string uvicornExe = Path.Combine(_repoRoot, @"apps\api\.venv\Scripts\uvicorn.exe");
                string nextBin = Path.Combine(_repoRoot, @"apps\web\node_modules\next\dist\bin\next");
                _pgCtlPath = Path.Combine(_repoRoot, @"apps\api\.venv\Lib\site-packages\pgserver\pginstall\bin\pg_ctl.exe");
                _pgDataDir = Path.Combine(_repoRoot, @"data\pgdata");

                if (!File.Exists(uvicornExe))
                {
                    FailAndWait("Ambiente Python da API nao encontrado em:\n" + uvicornExe + "\nExecute: uv sync --directory apps/api");
                    return 1;
                }
                if (!File.Exists(nextBin))
                {
                    FailAndWait("Dependencias do frontend nao encontradas em:\n" + nextBin + "\nExecute: npm --prefix apps/web install");
                    return 1;
                }
                if (!File.Exists(_pgCtlPath) || !Directory.Exists(_pgDataDir))
                {
                    FailAndWait("PostgreSQL local ou pasta data\\pgdata nao encontrada.");
                    return 1;
                }

                string nodeExe = FindExecutable("node.exe", new[]
                {
                    Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), @"Tools\node\node.exe"),
                    @"C:\Program Files\nodejs\node.exe",
                    @"C:\Program Files (x86)\nodejs\node.exe"
                });
                if (string.IsNullOrEmpty(nodeExe))
                {
                    FailAndWait("Node.js (node.exe) nao encontrado no PATH.");
                    return 1;
                }

                if (IsPortInUse(ApiPort))
                {
                    FailAndWait("A porta " + ApiPort + " (API FastAPI) ja esta em uso. Feche o outro processo e tente novamente.");
                    return 1;
                }
                if (IsPortInUse(WebPort))
                {
                    FailAndWait("A porta " + WebPort + " (Frontend Next.js) ja esta em uso. Feche o outro processo e tente novamente.");
                    return 1;
                }

                // 1. PostgreSQL 16
                Console.WriteLine("[2/4] Iniciando PostgreSQL 16 (porta " + PgPort + ")...");
                if (IsPortInUse(PgPort))
                {
                    Console.WriteLine("      PostgreSQL ja esta respondendo na porta " + PgPort + ".");
                }
                else
                {
                    if (!StartPostgres())
                    {
                        FailAndWait("Falha ao iniciar o PostgreSQL 16 em data\\pgdata.");
                        return 1;
                    }
                    _pgStartedByUs = true;
                }

                // 2. Build Next.js caso ainda nao exista
                string buildId = Path.Combine(_repoRoot, @"apps\web\.next\BUILD_ID");
                if (!File.Exists(buildId))
                {
                    Console.WriteLine("[*] Build de producao do frontend ainda nao existe. Gerando...");
                    int buildCode = RunCommand(nodeExe, "\"" + nextBin + "\" build", Path.Combine(_repoRoot, @"apps\web"));
                    if (buildCode != 0)
                    {
                        FailAndWait("Falha ao gerar o build do Next.js (codigo " + buildCode + ").");
                        ShutdownAll();
                        return 1;
                    }
                }

                // 3. FastAPI (Uvicorn)
                Console.WriteLine("[3/4] Iniciando API FastAPI em http://127.0.0.1:" + ApiPort + "...");
                var apiEnv = new Dictionary<string, string>
                {
                    { "DATABASE_URL", "postgresql://postgres@127.0.0.1:" + PgPort + "/postgres" }
                };
                _apiProcess = StartBackgroundProcess(
                    uvicornExe,
                    "cerrado_aberto_api.main:app --host 127.0.0.1 --port " + ApiPort,
                    Path.Combine(_repoRoot, @"apps\api"),
                    apiEnv,
                    "[API]"
                );

                if (!WaitForHttpOk("http://127.0.0.1:" + ApiPort + "/api/v1/health", 30))
                {
                    FailAndWait("A API FastAPI nao respondeu a tempo em http://127.0.0.1:" + ApiPort + "/api/v1/health.");
                    ShutdownAll();
                    return 1;
                }
                Console.WriteLine("      API FastAPI pronta!");

                // 4. Next.js
                Console.WriteLine("[4/4] Iniciando Frontend Next.js em http://127.0.0.1:" + WebPort + "...");
                var webEnv = new Dictionary<string, string>
                {
                    { "CERRADO_API_URL", "http://127.0.0.1:" + ApiPort }
                };
                _webProcess = StartBackgroundProcess(
                    nodeExe,
                    "\"" + nextBin + "\" start -H 127.0.0.1 -p " + WebPort,
                    Path.Combine(_repoRoot, @"apps\web"),
                    webEnv,
                    "[WEB]"
                );

                if (!WaitForHttpOk("http://127.0.0.1:" + WebPort + "/", 45))
                {
                    FailAndWait("O Frontend Next.js nao respondeu a tempo em http://127.0.0.1:" + WebPort + "/.");
                    ShutdownAll();
                    return 1;
                }

                Console.WriteLine();
                Console.WriteLine("=================================================================");
                Console.WriteLine("  Cerrado Aberto esta rodando em localhost!");
                Console.WriteLine("  Site (MVP):   http://127.0.0.1:" + WebPort);
                Console.WriteLine("  API OpenAPI:  http://127.0.0.1:" + ApiPort + "/docs");
                Console.WriteLine("  Banco local:  127.0.0.1:" + PgPort);
                Console.WriteLine("=================================================================");
                Console.WriteLine("Pressione ENTER ou Ctrl+C nesta janela para encerrar com seguranca.");
                Console.WriteLine();

                if (!noBrowser)
                {
                    try
                    {
                        Process.Start(new ProcessStartInfo
                        {
                            FileName = "http://127.0.0.1:" + WebPort,
                            UseShellExecute = true
                        });
                    }
                    catch
                    {
                        // Nao bloqueia se o navegador nao puder ser aberto automaticamente
                    }
                }

                // Aguarda ENTER ou encerramento de um dos processos principais
                bool enterPressed = false;
                if (Console.IsInputRedirected)
                {
                    ThreadPool.QueueUserWorkItem(_ =>
                    {
                        try
                        {
                            if (Console.ReadLine() != null)
                            {
                                enterPressed = true;
                            }
                        }
                        catch
                        {
                        }
                    });
                }

                while (!_shuttingDown && !enterPressed)
                {
                    if (!Console.IsInputRedirected && Console.KeyAvailable)
                    {
                        ConsoleKeyInfo key = Console.ReadKey(true);
                        if (key.Key == ConsoleKey.Enter)
                        {
                            break;
                        }
                    }
                    if (_apiProcess != null && _apiProcess.HasExited)
                    {
                        Console.WriteLine("[AVISO] O processo da API encerrou inesperadamente.");
                        break;
                    }
                    if (_webProcess != null && _webProcess.HasExited)
                    {
                        Console.WriteLine("[AVISO] O processo do Frontend encerrou inesperadamente.");
                        break;
                    }
                    Thread.Sleep(300);
                }

                ShutdownAll();
                return 0;
            }
            catch (Exception ex)
            {
                FailAndWait("Erro inesperado: " + ex.Message);
                ShutdownAll();
                return 1;
            }
        }

        private static void PrintBanner()
        {
            Console.WriteLine("=================================================================");
            Console.WriteLine("  Cerrado Aberto — Transparencia Legislativa de Inhumas (GO)");
            Console.WriteLine("  Inicializador local completo (PostgreSQL + FastAPI + Next.js)");
            Console.WriteLine("=================================================================");
            Console.WriteLine();
        }

        private static string FindRepoRoot()
        {
            string dir = AppDomain.CurrentDomain.BaseDirectory;
            for (int i = 0; i < 6 && !string.IsNullOrEmpty(dir); i++)
            {
                if (Directory.Exists(Path.Combine(dir, @"apps\api")) &&
                    Directory.Exists(Path.Combine(dir, @"apps\web")))
                {
                    return dir;
                }
                DirectoryInfo parent = Directory.GetParent(dir.TrimEnd('\\'));
                dir = parent != null ? parent.FullName : null;
            }
            return null;
        }

        private static string FindExecutable(string fileName, string[] fallbacks)
        {
            string pathEnv = Environment.GetEnvironmentVariable("PATH") ?? "";
            foreach (string folder in pathEnv.Split(';'))
            {
                if (string.IsNullOrWhiteSpace(folder)) continue;
                try
                {
                    string candidate = Path.Combine(folder.Trim(), fileName);
                    if (File.Exists(candidate)) return candidate;
                }
                catch { }
            }
            foreach (string fb in fallbacks)
            {
                if (File.Exists(fb)) return fb;
            }
            return null;
        }

        private static bool IsPortInUse(int port)
        {
            try
            {
                using (var client = new TcpClient())
                {
                    IAsyncResult res = client.BeginConnect("127.0.0.1", port, null, null);
                    bool ok = res.AsyncWaitHandle.WaitOne(TimeSpan.FromMilliseconds(350));
                    if (!ok) return false;
                    client.EndConnect(res);
                    return true;
                }
            }
            catch
            {
                return false;
            }
        }

        private static bool StartPostgres()
        {
            string args = string.Format(
                "-D \"{0}\" -w -t 60 -o \"-h 127.0.0.1 -p {1}\" start",
                _pgDataDir,
                PgPort);
            int exit = RunCommandNoRedirect(_pgCtlPath, args, _repoRoot);
            return exit == 0 && IsPortInUse(PgPort);
        }

        private static int RunCommandNoRedirect(string exe, string args, string workingDir)
        {
            var psi = new ProcessStartInfo
            {
                FileName = exe,
                Arguments = args,
                WorkingDirectory = workingDir,
                UseShellExecute = false,
                CreateNoWindow = true
            };
            using (var p = Process.Start(psi))
            {
                p.WaitForExit();
                return p.ExitCode;
            }
        }

        private static int RunCommand(string exe, string args, string workingDir)
        {
            var psi = new ProcessStartInfo
            {
                FileName = exe,
                Arguments = args,
                WorkingDirectory = workingDir,
                UseShellExecute = false,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                CreateNoWindow = true
            };
            using (var p = Process.Start(psi))
            {
                p.OutputDataReceived += (s, e) => { if (!string.IsNullOrEmpty(e.Data)) Console.WriteLine("      " + e.Data); };
                p.ErrorDataReceived += (s, e) => { if (!string.IsNullOrEmpty(e.Data)) Console.WriteLine("      " + e.Data); };
                p.BeginOutputReadLine();
                p.BeginErrorReadLine();
                p.WaitForExit();
                return p.ExitCode;
            }
        }

        private static Process StartBackgroundProcess(
            string exe,
            string args,
            string workingDir,
            Dictionary<string, string> extraEnv,
            string prefix)
        {
            var psi = new ProcessStartInfo
            {
                FileName = exe,
                Arguments = args,
                WorkingDirectory = workingDir,
                UseShellExecute = false,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                CreateNoWindow = true
            };
            if (extraEnv != null)
            {
                foreach (var kv in extraEnv)
                {
                    psi.EnvironmentVariables[kv.Key] = kv.Value;
                }
            }
            var p = new Process { StartInfo = psi };
            p.OutputDataReceived += (s, e) => { if (!string.IsNullOrEmpty(e.Data)) Console.WriteLine(prefix + " " + e.Data); };
            p.ErrorDataReceived += (s, e) => { if (!string.IsNullOrEmpty(e.Data)) Console.WriteLine(prefix + " " + e.Data); };
            p.Start();
            p.BeginOutputReadLine();
            p.BeginErrorReadLine();
            return p;
        }

        private static bool WaitForHttpOk(string url, int timeoutSeconds)
        {
            DateTime deadline = DateTime.UtcNow.AddSeconds(timeoutSeconds);
            while (DateTime.UtcNow < deadline && !_shuttingDown)
            {
                try
                {
                    var req = (HttpWebRequest)WebRequest.Create(url);
                    req.Timeout = 10000;
                    req.ReadWriteTimeout = 10000;
                    req.Method = "GET";
                    using (var resp = (HttpWebResponse)req.GetResponse())
                    {
                        if ((int)resp.StatusCode == 200)
                        {
                            return true;
                        }
                    }
                }
                catch
                {
                    // Continua tentando ate o deadline
                }
                Thread.Sleep(500);
            }
            return false;
        }

        private static bool OnConsoleCtrl(int ctrlType)
        {
            ShutdownAll();
            return false;
        }

        private static void ShutdownAll()
        {
            lock (ShutdownLock)
            {
                if (_shuttingDown) return;
                _shuttingDown = true;

                Console.WriteLine();
                Console.WriteLine("Encerrando servicos com seguranca...");

                KillProcessTree(_webProcess);
                KillProcessTree(_apiProcess);

                if (_pgStartedByUs && File.Exists(_pgCtlPath) && Directory.Exists(_pgDataDir))
                {
                    Console.WriteLine("Parando PostgreSQL 16 (modo fast)...");
                    RunCommandNoRedirect(_pgCtlPath, string.Format("-D \"{0}\" -m fast -w stop", _pgDataDir), _repoRoot);
                }
                Console.WriteLine("Tudo encerrado.");
            }
        }

        private static void KillProcessTree(Process p)
        {
            if (p == null) return;
            try
            {
                if (!p.HasExited)
                {
                    var killer = new ProcessStartInfo
                    {
                        FileName = "taskkill.exe",
                        Arguments = "/PID " + p.Id + " /T /F",
                        UseShellExecute = false,
                        CreateNoWindow = true,
                        RedirectStandardOutput = true,
                        RedirectStandardError = true
                    };
                    using (var k = Process.Start(killer))
                    {
                        k.WaitForExit(5000);
                    }
                }
            }
            catch { }
        }

        private static void FailAndWait(string message)
        {
            Console.WriteLine();
            Console.WriteLine("[ERRO] " + message);
            Console.WriteLine("Pressione ENTER para sair...");
            try
            {
                if (!Console.IsInputRedirected)
                {
                    Console.ReadLine();
                }
            }
            catch { }
        }
    }
}
