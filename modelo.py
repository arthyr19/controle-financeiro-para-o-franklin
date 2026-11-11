"""Modelo de dados do controle financeiro."""

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

RECEITA = "receita"
DESPESA = "despesa"
TIPOS_VALIDOS = (RECEITA, DESPESA)
CAMPOS_OBRIGATORIOS = ("id", "tipo", "descricao", "valor", "categoria", "data")
CENTAVOS = Decimal("0.01")


def para_decimal(valor: Decimal | int | float | str) -> Decimal:
    """Converte para Decimal com 2 casas (arredondamento escolar: 0,005 vira 0,01).

    Lança ValueError se não for um número finito.
    """
    if isinstance(valor, bool) or not isinstance(valor, (Decimal, int, float, str)):
        raise ValueError(f"valor inválido: {valor!r}.")
    try:
        # float passa por str() antes, senão 99.9 viraria 99.900000000000005684...
        numero = Decimal(str(valor)) if isinstance(valor, float) else Decimal(valor)
        if not numero.is_finite():
            raise ValueError(f"valor inválido: {valor!r}.")
        return numero.quantize(CENTAVOS, rounding=ROUND_HALF_UP)
    except InvalidOperation:
        raise ValueError(f"valor inválido: {valor!r}.") from None


@dataclass
class Transacao:
    """Representa uma movimentação financeira (receita ou despesa)."""

    id: int
    tipo: str
    descricao: str
    valor: Decimal
    categoria: str
    data: date

    def para_dict(self) -> dict:
        """Converte a transação em um dicionário serializável (JSON)."""
        return {
            "id": self.id,
            "tipo": self.tipo,
            "descricao": self.descricao,
            # Salvo como texto ("16.00") para não perder precisão no JSON.
            "valor": str(self.valor),
            "categoria": self.categoria,
            "data": self.data.isoformat(),
        }

    @classmethod
    def de_dict(cls, dados: dict) -> "Transacao":
        """Cria uma transação a partir de um dicionário (lido do JSON).

        Valida cada campo e lança ValueError se algum estiver faltando ou errado.
        """
        if not isinstance(dados, dict):
            raise ValueError("o registro não é um objeto JSON.")

        campos_faltando = [c for c in CAMPOS_OBRIGATORIOS if c not in dados]
        if campos_faltando:
            raise ValueError(f"campos ausentes: {', '.join(campos_faltando)}.")

        id_transacao = dados["id"]
        # bool é subclasse de int, então True/False precisam ser barrados à parte.
        if not isinstance(id_transacao, int) or isinstance(id_transacao, bool) or id_transacao <= 0:
            raise ValueError(f"ID inválido: {id_transacao!r}.")

        tipo = dados["tipo"]
        if tipo not in TIPOS_VALIDOS:
            raise ValueError(f"tipo inválido: {tipo!r}.")

        descricao = dados["descricao"]
        if not isinstance(descricao, str) or not descricao.strip():
            raise ValueError("a descrição deve ser um texto não vazio.")

        # Aceita texto ("16.00", formato atual) e número (16.0, arquivos antigos).
        valor = para_decimal(dados["valor"])
        if valor <= 0:
            raise ValueError(f"valor inválido: {dados['valor']!r}.")

        categoria = dados["categoria"]
        if not isinstance(categoria, str) or not categoria.strip():
            raise ValueError("a categoria deve ser um texto não vazio.")

        try:
            data = date.fromisoformat(dados["data"])
        except (TypeError, ValueError):
            raise ValueError(f"data inválida: {dados['data']!r}.") from None

        return cls(
            id=id_transacao,
            tipo=tipo,
            descricao=descricao,
            valor=valor,
            categoria=categoria,
            data=data,
        )
