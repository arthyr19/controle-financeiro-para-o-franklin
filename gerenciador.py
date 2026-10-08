"""Regras de negócio e persistência do controle financeiro."""

import csv
import json
from datetime import date
from pathlib import Path

from modelo import DESPESA, RECEITA, TIPOS_VALIDOS, Transacao


class GerenciadorFinanceiro:
    """Gerencia as transações e salva tudo em um arquivo JSON."""

    def __init__(self, arquivo: str | Path):
        self.arquivo = Path(arquivo)
        self.transacoes: list[Transacao] = []
        self._carregar()

    # ---------- Persistência ----------

    def _carregar(self) -> None:
        if not self.arquivo.exists():
            return
        with open(self.arquivo, encoding="utf-8") as f:
            dados = json.load(f)
        self.transacoes = [Transacao.de_dict(item) for item in dados]

    def _salvar(self) -> None:
        self.arquivo.parent.mkdir(parents=True, exist_ok=True)
        with open(self.arquivo, "w", encoding="utf-8") as f:
            json.dump(
                [t.para_dict() for t in self.transacoes],
                f,
                ensure_ascii=False,
                indent=2,
            )

    def _proximo_id(self) -> int:
        return max((t.id for t in self.transacoes), default=0) + 1

    # ---------- Cadastro ----------

    def adicionar(
        self,
        tipo: str,
        descricao: str,
        valor: float,
        categoria: str,
        data: date | None = None,
    ) -> Transacao:
        """Valida e registra uma nova transação."""
        if tipo not in TIPOS_VALIDOS:
            raise ValueError(f"Tipo inválido: {tipo}")
        if valor <= 0:
            raise ValueError("O valor deve ser maior que zero.")
        if not descricao.strip():
            raise ValueError("A descrição não pode ser vazia.")

        transacao = Transacao(
            id=self._proximo_id(),
            tipo=tipo,
            descricao=descricao.strip(),
            valor=round(valor, 2),
            categoria=categoria.strip().lower() or "outros",
            data=data or date.today(),
        )
        self.transacoes.append(transacao)
        self._salvar()
        return transacao

    def adicionar_receita(self, descricao, valor, categoria, data=None) -> Transacao:
        return self.adicionar(RECEITA, descricao, valor, categoria, data)

    def adicionar_despesa(self, descricao, valor, categoria, data=None) -> Transacao:
        return self.adicionar(DESPESA, descricao, valor, categoria, data)

    # ---------- Consultas ----------

    def listar(self) -> list[Transacao]:
        """Retorna todas as transações ordenadas por data."""
        return sorted(self.transacoes, key=lambda t: (t.data, t.id))

    @staticmethod
    def _totais(transacoes: list[Transacao]) -> dict:
        receitas = sum(t.valor for t in transacoes if t.tipo == RECEITA)
        despesas = sum(t.valor for t in transacoes if t.tipo == DESPESA)
        return {
            "receitas": round(receitas, 2),
            "despesas": round(despesas, 2),
            "saldo": round(receitas - despesas, 2),
        }

    def saldo(self) -> dict:
        """Total de receitas, despesas e saldo geral."""
        return self._totais(self.transacoes)

    def categorias(self) -> list[str]:
        return sorted({t.categoria for t in self.transacoes})

    def filtrar_por_categoria(self, categoria: str) -> list[Transacao]:
        categoria = categoria.strip().lower()
        return [t for t in self.listar() if t.categoria == categoria]

    def relatorio_mensal(self, ano: int, mes: int) -> dict:
        """Resumo de um mês: totais, gastos por categoria e transações."""
        do_mes = [t for t in self.listar() if t.data.year == ano and t.data.month == mes]

        despesas_por_categoria: dict[str, float] = {}
        for t in do_mes:
            if t.tipo == DESPESA:
                despesas_por_categoria[t.categoria] = round(
                    despesas_por_categoria.get(t.categoria, 0) + t.valor, 2
                )

        return {
            **self._totais(do_mes),
            "despesas_por_categoria": dict(
                sorted(despesas_por_categoria.items(), key=lambda item: item[1], reverse=True)
            ),
            "transacoes": do_mes,
        }

    # ---------- Exportação ----------

    def exportar_csv(self, caminho: str | Path) -> Path:
        """Exporta as transações para CSV (separador ';', abre direto no Excel)."""
        caminho = Path(caminho)
        caminho.parent.mkdir(parents=True, exist_ok=True)
        with open(caminho, "w", newline="", encoding="utf-8-sig") as f:
            escritor = csv.writer(f, delimiter=";")
            escritor.writerow(["id", "data", "tipo", "categoria", "descricao", "valor"])
            for t in self.listar():
                escritor.writerow([
                    t.id,
                    t.data.strftime("%d/%m/%Y"),
                    t.tipo,
                    t.categoria,
                    t.descricao,
                    f"{t.valor:.2f}".replace(".", ","),
                ])
        return caminho
