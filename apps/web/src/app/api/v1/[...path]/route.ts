import { NextRequest, NextResponse } from "next/server";

const API_BASE = (process.env.CERRADO_API_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

/**
 * Proxy somente leitura (apenas GET) para a API FastAPI v1 em ambiente de homologação.
 * Evita problemas de CORS no navegador e bloqueia qualquer método de escrita.
 */
export async function GET(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
): Promise<NextResponse> {
  const { path } = await context.params;
  const safePath = path.map((segment) => encodeURIComponent(segment)).join("/");
  const search = request.nextUrl.searchParams.toString();
  const targetUrl = `${API_BASE}/api/v1/${safePath}${search ? `?${search}` : ""}`;

  try {
    const response = await fetch(targetUrl, {
      method: "GET",
      headers: {
        Accept: "application/json",
      },
      cache: "no-store",
    });

    const bodyText = await response.text();
    return new NextResponse(bodyText, {
      status: response.status,
      headers: {
        "Content-Type": response.headers.get("Content-Type") || "application/json; charset=utf-8",
        "Cache-Control": "no-store",
      },
    });
  } catch {
    return NextResponse.json(
      {
        detail:
          "Não foi possível conectar à API FastAPI do Cerrado Aberto. Verifique se o backend está em execução.",
      },
      { status: 502 },
    );
  }
}
