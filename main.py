"""Interface de linha de comando do controle financeiro."""

from datetime import date, datetime
from pathlib import Path

from gerenciador import GerenciadorFinanceiro
from modelo import RECEITA, Transacao

PASTA_BASE = Path(__file__).parent
ARQUIVO_DADOS = PASTA_BASE / "dados" / "transacoes.json"
PASTA_EXPORTACAO = PASTA_BASE / "exportacoes"

MENU = """
========== CONTROLE FINANCEIRO ==========
 1 - Adicionar receita
 2 - Adicionar despesa
 3 - Listar transações
 4 - Mostrar saldo
 5 - Filtrar por categoria
 6 - Relatório mensal
 7 - Exportar dados (CSV)
 8 - Sair
=========================================="""


# Utilitários de formatação e entrada 

def formatar_moeda(valor: float) -> str:
    """Formata no padrão brasileiro: R$ 1.234,56"""
    texto = f"{abs(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    sinal = "-" if valor < 0 else ""
    return f"{sinal}R$ {texto}"


def ler_valor(mensagem: str) -> float:
    while True:
        entrada = input(mensagem).strip().replace("R$", "").replace(" ", "")
        # Aceita "1.234,56", "1234,56" e "1234.56"
        if "," in entrada:
            entrada = entrada.replace(".", "").replace(",", ".")
        try:
            valor = float(entrada)
            if valor > 0:
                return valor
            print("  O valor deve ser maior que zero.")
        except ValueError:
            print("  Valor inválido. Exemplo: 150,90")


def ler_texto(mensagem: str, obrigatorio: bool = True) -> str:
    while True:
        texto = input(mensagem).strip()
        if texto or not obrigatorio:
            return texto
        print("  Este campo é obrigatório.")


def ler_data(mensagem: str) -> date:
    while True:
        entrada = input(mensagem).strip()
        if not entrada:
            return date.today()
        try:
            return datetime.strptime(entrada, "%d/%m/%Y").date()
        except ValueError:
            print("  Data inválida. Use o formato DD/MM/AAAA.")


def ler_mes_ano() -> tuple[int, int]:
    while True:
        entrada = input("Mês/ano (MM/AAAA) [Enter = mês atual]: ").strip()
        if not entrada:
            hoje = date.today()
            return hoje.year, hoje.month
        try:
            data = datetime.strptime(entrada, "%m/%Y")
            return data.year, data.month
        except ValueError:
            print("  Formato inválido. Exemplo: 03/2026")


def imprimir_transacoes(transacoes: list[Transacao]) -> None:
    if not transacoes:
        print("\nNenhuma transação encontrada.")
        return

    print(f"\n{'ID':>4}  {'DATA':<10}  {'TIPO':<8}  {'CATEGORIA':<14}  {'DESCRIÇÃO':<24}  {'VALOR':>14}")
    print("-" * 86)
    for t in transacoes:
        valor = t.valor if t.tipo == RECEITA else -t.valor
        print(
            f"{t.id:>4}  {t.data.strftime('%d/%m/%Y'):<10}  {t.tipo:<8}  "
            f"{t.categoria[:14]:<14}  {t.descricao[:24]:<24}  {formatar_moeda(valor):>14}"
        )


def imprimir_totais(totais: dict) -> None:
    print(f"  Receitas: {formatar_moeda(totais['receitas']):>16}")
    print(f"  Despesas: {formatar_moeda(totais['despesas']):>16}")
    print(f"  Saldo:    {formatar_moeda(totais['saldo']):>16}")


#  Ações do menu 

def adicionar_transacao(gerenciador: GerenciadorFinanceiro, tipo: str) -> None:
    print(f"\n--- Nova {tipo} ---")
    descricao = ler_texto("Descrição: ")
    valor = ler_valor("Valor: R$ ")
    categoria = ler_texto("Categoria (ex: salário, mercado, lazer): ", obrigatorio=False)
    data = ler_data("Data (DD/MM/AAAA) [Enter = hoje]: ")

    transacao = gerenciador.adicionar(tipo, descricao, valor, categoria, data)
    print(f"\n{tipo.capitalize()} #{transacao.id} registrada: {formatar_moeda(transacao.valor)}")


def listar_transacoes(gerenciador: GerenciadorFinanceiro) -> None:
    print("\n--- Transações ---")
    imprimir_transacoes(gerenciador.listar())


def mostrar_saldo(gerenciador: GerenciadorFinanceiro) -> None:
    print("\n--- Saldo geral ---")
    imprimir_totais(gerenciador.saldo())


def filtrar_categoria(gerenciador: GerenciadorFinanceiro) -> None:
    categorias = gerenciador.categorias()
    if not categorias:
        print("\nNenhuma transação cadastrada ainda.")
        return

    print("\nCategorias disponíveis: " + ", ".join(categorias))
    categoria = ler_texto("Categoria: ")
    transacoes = gerenciador.filtrar_por_categoria(categoria)
    imprimir_transacoes(transacoes)
    if transacoes:
        total = sum(t.valor if t.tipo == RECEITA else -t.valor for t in transacoes)
        print(f"\nTotal na categoria: {formatar_moeda(total)}")


def relatorio_mensal(gerenciador: GerenciadorFinanceiro) -> None:
    ano, mes = ler_mes_ano()
    relatorio = gerenciador.relatorio_mensal(ano, mes)

    print(f"\n--- Relatório de {mes:02d}/{ano} ---")
    imprimir_totais(relatorio)

    gastos = relatorio["despesas_por_categoria"]
    if gastos:
        print("\n  Despesas por categoria:")
        for categoria, valor in gastos.items():
            percentual = valor / relatorio["despesas"] * 100
            barra = "█" * round(percentual / 5)
            print(f"  {categoria[:14]:<14} {formatar_moeda(valor):>14}  {percentual:5.1f}% {barra}")

    imprimir_transacoes(relatorio["transacoes"])


def exportar_dados(gerenciador: GerenciadorFinanceiro) -> None:
    if not gerenciador.transacoes:
        print("\nNão há transações para exportar.")
        return
    nome = f"transacoes_{datetime.now():%Y%m%d_%H%M%S}.csv"
    caminho = gerenciador.exportar_csv(PASTA_EXPORTACAO / nome)
    print(f"\nDados exportados para: {caminho}")


#  Loop principal 

def main() -> None:
    gerenciador = GerenciadorFinanceiro(ARQUIVO_DADOS)

    acoes = {
        "1": lambda: adicionar_transacao(gerenciador, "receita"),
        "2": lambda: adicionar_transacao(gerenciador, "despesa"),
        "3": lambda: listar_transacoes(gerenciador),
        "4": lambda: mostrar_saldo(gerenciador),
        "5": lambda: filtrar_categoria(gerenciador),
        "6": lambda: relatorio_mensal(gerenciador),
        "7": lambda: exportar_dados(gerenciador),
    }

    while True:
        print(MENU)
        opcao = input("Escolha uma opção: ").strip()

        if opcao == "8":
            print("\nAté logo!")
            break

        acao = acoes.get(opcao)
        if acao is None:
            print("\nOpção inválida, tente novamente.")
            continue

        try:
            acao()
        except ValueError as erro:
            print(f"\nErro: {erro}")

        input("\nPressione Enter para continuar...")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\n\nPrograma encerrado.")
