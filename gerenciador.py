"""Regras de negócio e persistência do controle financeiro."""

import csv
import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from modelo import DESPESA, RECEITA, TIPOS_VALIDOS, Transacao, para_decimal


class TransacaoNaoEncontrada(ValueError):
    """Lançada quando não existe transação com o ID informado."""

    def __init__(self, id_transacao: int):
        super().__init__(f"Nenhuma transação encontrada com o ID {id_transacao}.")


class ArquivoDeDadosInvalido(Exception):
    """Lançada quando o arquivo JSON não pode ser lido ou tem dados inválidos."""

    def __init__(self, arquivo: Path, motivo: str):
        self.arquivo = arquivo
        self.motivo = motivo
        super().__init__(f"Não foi possível carregar '{arquivo}': {motivo}")


class ErroAoSalvar(Exception):
    """Lançada quando não foi possível gravar as transações no arquivo."""

    def __init__(self, arquivo: Path, erro: OSError):
        self.arquivo = arquivo
        super().__init__(f"Não foi possível salvar em '{arquivo}' ({erro}). Nada foi alterado.")


class GerenciadorFinanceiro:
    """Gerencia as transações e salva tudo em um arquivo JSON."""

    def __init__(self, arquivo: str | Path):
        self.arquivo = Path(arquivo)
        self.transacoes: list[Transacao] = []
        self._carregar()

    #  Persistência 

    def _carregar(self) -> None:
        """Lê o arquivo JSON. Se algo estiver errado, avisa e não mexe no arquivo."""
        if not self.arquivo.exists():
            return

        try:
            with open(self.arquivo, encoding="utf-8") as f:
                # parse_float=Decimal: valores antigos salvos como número não passam por float.
                dados = json.load(f, parse_float=Decimal)
        except json.JSONDecodeError as erro:
            raise ArquivoDeDadosInvalido(
                self.arquivo, f"JSON corrompido (linha {erro.lineno}, coluna {erro.colno})."
            ) from erro
        except UnicodeDecodeError as erro:
            raise ArquivoDeDadosInvalido(self.arquivo, "o arquivo não está em UTF-8.") from erro
        except OSError as erro:
            raise ArquivoDeDadosInvalido(self.arquivo, f"erro ao abrir o arquivo ({erro}).") from erro

        if not isinstance(dados, list):
            raise ArquivoDeDadosInvalido(self.arquivo, "era esperada uma lista de transações.")

        transacoes = []
        ids_vistos = set()
        for posicao, item in enumerate(dados, start=1):
            try:
                transacao = Transacao.de_dict(item)
            except ValueError as erro:
                raise ArquivoDeDadosInvalido(
                    self.arquivo, f"registro {posicao} inválido: {erro}"
                ) from erro
            if transacao.id in ids_vistos:
                raise ArquivoDeDadosInvalido(
                    self.arquivo, f"registro {posicao} repete o ID {transacao.id}."
                )
            ids_vistos.add(transacao.id)
            transacoes.append(transacao)

        self.transacoes = transacoes

    def _salvar(self) -> None:
        """Grava primeiro num arquivo temporário e só depois troca pelo original.

        Assim, se der erro no meio da escrita, o JSON antigo continua inteiro.
        """
        temporario = self.arquivo.with_name(self.arquivo.name + ".tmp")
        try:
            self.arquivo.parent.mkdir(parents=True, exist_ok=True)
            with open(temporario, "w", encoding="utf-8") as f:
                json.dump(
                    [t.para_dict() for t in self.transacoes],
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
            temporario.replace(self.arquivo)
        except OSError as erro:
            temporario.unlink(missing_ok=True)
            raise ErroAoSalvar(self.arquivo, erro) from erro

    def _proximo_id(self) -> int:
        return max((t.id for t in self.transacoes), default=0) + 1

    #  Validação

    @staticmethod
    def _validar_id(id_transacao: int) -> int:
        # bool é subclasse de int, então True/False precisam ser barrados à parte.
        if not isinstance(id_transacao, int) or isinstance(id_transacao, bool) or id_transacao <= 0:
            raise ValueError(f"ID inválido: {id_transacao!r}. Use um número inteiro positivo.")
        return id_transacao

    @staticmethod
    def _validar_descricao(descricao: str) -> str:
        if not isinstance(descricao, str) or not descricao.strip():
            raise ValueError("A descrição não pode ser vazia.")
        return descricao.strip()

    @staticmethod
    def _validar_valor(valor: Decimal | int | float) -> Decimal:
        # Texto é convertido na interface (main.py); aqui só entram números.
        if isinstance(valor, str):
            raise ValueError("O valor deve ser um número.")
        try:
            valor = para_decimal(valor)
        except ValueError:
            raise ValueError("O valor deve ser um número finito.") from None
        if valor <= 0:
            raise ValueError("O valor deve ser maior que zero (mínimo R$ 0,01).")
        return valor

    @staticmethod
    def _normalizar_categoria(categoria: str) -> str:
        if not isinstance(categoria, str):
            raise ValueError("A categoria deve ser um texto.")
        return categoria.strip().lower() or "outros"

    @staticmethod
    def _validar_data(data: date) -> date:
        if not isinstance(data, date):
            raise ValueError("A data informada é inválida.")
        # datetime também é date; guardamos só a parte da data.
        if isinstance(data, datetime):
            return data.date()
        return data

    #  Cadastro

    def adicionar(
        self,
        tipo: str,
        descricao: str,
        valor: Decimal | int | float,
        categoria: str,
        data: date | None = None,
    ) -> Transacao:
        """Valida e registra uma nova transação."""
        if tipo not in TIPOS_VALIDOS:
            raise ValueError(f"Tipo inválido: {tipo}")

        transacao = Transacao(
            id=self._proximo_id(),
            tipo=tipo,
            descricao=self._validar_descricao(descricao),
            valor=self._validar_valor(valor),
            categoria=self._normalizar_categoria(categoria),
            data=self._validar_data(data) if data is not None else date.today(),
        )
        self.transacoes.append(transacao)
        try:
            self._salvar()
        except ErroAoSalvar:
            self.transacoes.remove(transacao)
            raise
        return transacao

    def adicionar_receita(self, descricao, valor, categoria, data=None) -> Transacao:
        return self.adicionar(RECEITA, descricao, valor, categoria, data)

    def adicionar_despesa(self, descricao, valor, categoria, data=None) -> Transacao:
        return self.adicionar(DESPESA, descricao, valor, categoria, data)

    #  Edição e exclusão

    def buscar(self, id_transacao: int) -> Transacao:
        """Retorna a transação com o ID informado ou lança TransacaoNaoEncontrada."""
        self._validar_id(id_transacao)
        for transacao in self.transacoes:
            if transacao.id == id_transacao:
                return transacao
        raise TransacaoNaoEncontrada(id_transacao)

    def editar(
        self,
        id_transacao: int,
        descricao: str | None = None,
        valor: Decimal | int | float | None = None,
        categoria: str | None = None,
        data: date | None = None,
    ) -> Transacao:
        """Altera os campos informados. Campos deixados como None não mudam."""
        transacao = self.buscar(id_transacao)

        # Valida tudo antes de alterar, para nunca deixar a transação pela metade.
        alteracoes = {}
        if descricao is not None:
            alteracoes["descricao"] = self._validar_descricao(descricao)
        if valor is not None:
            alteracoes["valor"] = self._validar_valor(valor)
        if categoria is not None:
            alteracoes["categoria"] = self._normalizar_categoria(categoria)
        if data is not None:
            alteracoes["data"] = self._validar_data(data)

        # Se nada mudou de fato, não precisa regravar o arquivo.
        alteracoes = {c: v for c, v in alteracoes.items() if getattr(transacao, c) != v}
        if not alteracoes:
            return transacao

        anteriores = {campo: getattr(transacao, campo) for campo in alteracoes}
        for campo, novo_valor in alteracoes.items():
            setattr(transacao, campo, novo_valor)
        try:
            self._salvar()
        except ErroAoSalvar:
            for campo, valor_antigo in anteriores.items():
                setattr(transacao, campo, valor_antigo)
            raise
        return transacao

    def excluir(self, id_transacao: int) -> Transacao:
        """Remove a transação com o ID informado e retorna o que foi removido."""
        transacao = self.buscar(id_transacao)
        posicao = self.transacoes.index(transacao)
        self.transacoes.pop(posicao)
        try:
            self._salvar()
        except ErroAoSalvar:
            self.transacoes.insert(posicao, transacao)
            raise
        return transacao

    #  Consultas

    def listar(self) -> list[Transacao]:
        """Retorna todas as transações ordenadas por data."""
        return sorted(self.transacoes, key=lambda t: (t.data, t.id))

    @staticmethod
    def _totais(transacoes: list[Transacao]) -> dict:
        # Somas com Decimal são exatas, então não precisa de round().
        receitas = sum((t.valor for t in transacoes if t.tipo == RECEITA), Decimal("0.00"))
        despesas = sum((t.valor for t in transacoes if t.tipo == DESPESA), Decimal("0.00"))
        return {
            "receitas": receitas,
            "despesas": despesas,
            "saldo": receitas - despesas,
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

        despesas_por_categoria: dict[str, Decimal] = {}
        for t in do_mes:
            if t.tipo == DESPESA:
                despesas_por_categoria[t.categoria] = (
                    despesas_por_categoria.get(t.categoria, Decimal("0.00")) + t.valor
                )

        return {
            **self._totais(do_mes),
            "despesas_por_categoria": dict(
                sorted(despesas_por_categoria.items(), key=lambda item: item[1], reverse=True)
            ),
            "transacoes": do_mes,
        }

    # Exportação

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
