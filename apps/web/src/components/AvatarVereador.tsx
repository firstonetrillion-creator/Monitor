import { obterIniciais } from "@/lib/format";

interface AvatarVereadorProps {
  nome: string;
  tamanho?: "sm" | "md" | "lg";
}

export function AvatarVereador({ nome, tamanho = "md" }: AvatarVereadorProps) {
  const iniciais = obterIniciais(nome);
  const sizeClass =
    tamanho === "lg"
      ? "w-16 h-16 text-xl"
      : tamanho === "sm"
        ? "w-9 h-9 text-xs"
        : "w-12 h-12 text-sm";

  return (
    <div
      aria-hidden="true"
      className={`${sizeClass} shrink-0 rounded-full bg-[var(--primary)] text-[var(--primary-ink)] font-display font-bold flex items-center justify-center select-none`}
    >
      {iniciais}
    </div>
  );
}
