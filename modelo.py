"""Modelo de dados do controle financeiro."""

from dataclasses import dataclass
from datetime import date

RECEITA = "receita"
DESPESA = "despesa"
TIPOS_VALIDOS = (RECEITA, DESPESA)


@dataclass
class Transacao:
    """Representa uma movimentação financeira (receita ou despesa)."""

    id: int
    tipo: str
    descricao: str
    valor: float
    categoria: str
    data: date

    def para_dict(self) -> dict:
        """Converte a transação em um dicionário serializável (JSON)."""
        return {
            "id": self.id,
            "tipo": self.tipo,
            "descricao": self.descricao,
            "valor": self.valor,
            "categoria": self.categoria,
            "data": self.data.isoformat(),
        }

    @classmethod
    def de_dict(cls, dados: dict) -> "Transacao":
        """Cria uma transação a partir de um dicionário (lido do JSON)."""
        return cls(
            id=dados["id"],
            tipo=dados["tipo"],
            descricao=dados["descricao"],
            valor=float(dados["valor"]),
            categoria=dados["categoria"],
            data=date.fromisoformat(dados["data"]),
        )
