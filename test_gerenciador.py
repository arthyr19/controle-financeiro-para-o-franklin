"""Testes automatizados. Execute com: python -m unittest -v"""

import csv
import tempfile
import unittest
from datetime import date
from pathlib import Path

from gerenciador import GerenciadorFinanceiro


class TestGerenciadorFinanceiro(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.arquivo = Path(self.pasta.name) / "transacoes.json"
        self.g = GerenciadorFinanceiro(self.arquivo)

    def tearDown(self):
        self.pasta.cleanup()

    def test_saldo(self):
        self.g.adicionar_receita("Salário", 3000, "salário")
        self.g.adicionar_despesa("Mercado", 450.50, "mercado")
        self.assertEqual(
            self.g.saldo(), {"receitas": 3000, "despesas": 450.5, "saldo": 2549.5}
        )

    def test_valor_invalido(self):
        with self.assertRaises(ValueError):
            self.g.adicionar_despesa("Nada", 0, "outros")

    def test_persistencia(self):
        self.g.adicionar_receita("Freela", 800, "trabalho")
        recarregado = GerenciadorFinanceiro(self.arquivo)
        self.assertEqual(len(recarregado.transacoes), 1)
        self.assertEqual(recarregado.transacoes[0].descricao, "Freela")

    def test_filtrar_por_categoria_ignora_maiusculas(self):
        self.g.adicionar_despesa("Cinema", 40, "Lazer")
        self.g.adicionar_despesa("Aluguel", 1200, "moradia")
        resultado = self.g.filtrar_por_categoria("LAZER")
        self.assertEqual([t.descricao for t in resultado], ["Cinema"])

    def test_relatorio_mensal(self):
        self.g.adicionar_receita("Salário", 3000, "salário", date(2026, 3, 5))
        self.g.adicionar_despesa("Mercado", 300, "mercado", date(2026, 3, 10))
        self.g.adicionar_despesa("Feira", 100, "mercado", date(2026, 3, 12))
        self.g.adicionar_despesa("Luz", 150, "contas", date(2026, 4, 1))

        relatorio = self.g.relatorio_mensal(2026, 3)
        self.assertEqual(relatorio["saldo"], 2600)
        self.assertEqual(relatorio["despesas_por_categoria"], {"mercado": 400})
        self.assertEqual(len(relatorio["transacoes"]), 3)

    def test_exportar_csv(self):
        self.g.adicionar_despesa("Mercado", 99.9, "mercado", date(2026, 3, 10))
        caminho = self.g.exportar_csv(Path(self.pasta.name) / "saida.csv")
        with open(caminho, encoding="utf-8-sig") as f:
            linhas = list(csv.reader(f, delimiter=";"))
        self.assertEqual(linhas[0][0], "id")
        self.assertEqual(linhas[1], ["1", "10/03/2026", "despesa", "mercado", "Mercado", "99,90"])


if __name__ == "__main__":
    unittest.main()
