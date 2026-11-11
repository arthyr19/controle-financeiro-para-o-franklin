

import csv
import json
import tempfile
import unittest
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from unittest import mock

from gerenciador import (
    ArquivoDeDadosInvalido,
    ErroAoSalvar,
    GerenciadorFinanceiro,
    TransacaoNaoEncontrada,
)


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


class TestEdicaoEExclusao(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.arquivo = Path(self.pasta.name) / "transacoes.json"
        self.g = GerenciadorFinanceiro(self.arquivo)
        self.mercado = self.g.adicionar_despesa("Mercado", 100, "mercado", date(2026, 3, 10))
        self.salario = self.g.adicionar_receita("Salário", 3000, "salário", date(2026, 3, 5))

    def tearDown(self):
        self.pasta.cleanup()

    def recarregar(self) -> GerenciadorFinanceiro:
        """Simula reiniciar o programa: cria um gerenciador novo lendo o mesmo arquivo."""
        return GerenciadorFinanceiro(self.arquivo)

    # Exclusão

    def test_excluir_remove_a_transacao(self):
        self.g.excluir(self.mercado.id)
        self.assertEqual([t.descricao for t in self.g.listar()], ["Salário"])
        self.assertEqual(self.g.saldo()["despesas"], 0)

    def test_excluir_id_inexistente(self):
        with self.assertRaises(TransacaoNaoEncontrada):
            self.g.excluir(999)
        self.assertEqual(len(self.g.transacoes), 2)

    def test_exclusao_persiste_apos_reiniciar(self):
        self.g.excluir(self.mercado.id)
        recarregado = self.recarregar()
        self.assertEqual([t.id for t in recarregado.transacoes], [self.salario.id])

    # Edição

    def test_editar_todos_os_campos(self):
        self.g.editar(
            self.mercado.id,
            descricao="Feira",
            valor=55.5,
            categoria="Alimentação",
            data=date(2026, 4, 1),
        )
        t = self.g.buscar(self.mercado.id)
        self.assertEqual(
            (t.descricao, t.valor, t.categoria, t.data),
            ("Feira", 55.5, "alimentação", date(2026, 4, 1)),
        )

    def test_editar_apenas_um_campo_mantem_os_outros(self):
        self.g.editar(self.mercado.id, valor=80)
        t = self.g.buscar(self.mercado.id)
        self.assertEqual(
            (t.descricao, t.valor, t.categoria, t.data),
            ("Mercado", 80, "mercado", date(2026, 3, 10)),
        )

    def test_editar_id_inexistente(self):
        with self.assertRaises(TransacaoNaoEncontrada):
            self.g.editar(999, descricao="Fantasma")

    def test_editar_com_valor_invalido_nao_altera_nada(self):
        with self.assertRaises(ValueError):
            self.g.editar(self.mercado.id, descricao="Feira", valor=-10)
        t = self.g.buscar(self.mercado.id)
        self.assertEqual((t.descricao, t.valor), ("Mercado", 100))

    def test_editar_com_descricao_vazia(self):
        with self.assertRaises(ValueError):
            self.g.editar(self.mercado.id, descricao="   ")

    def test_edicao_persiste_apos_reiniciar(self):
        self.g.editar(self.mercado.id, descricao="Feira", valor=55.5)
        t = self.recarregar().buscar(self.mercado.id)
        self.assertEqual((t.descricao, t.valor), ("Feira", 55.5))

    # Busca

    def test_mensagem_de_id_inexistente(self):
        with self.assertRaises(TransacaoNaoEncontrada) as contexto:
            self.g.buscar(42)
        self.assertEqual(str(contexto.exception), "Nenhuma transação encontrada com o ID 42.")

    def test_buscar_retorna_a_transacao_certa(self):
        self.assertIs(self.g.buscar(self.salario.id), self.salario)

    def test_buscar_com_id_invalido(self):
        for id_invalido in (0, -1, "1", 1.0, True, None):
            with self.subTest(id=id_invalido):
                with self.assertRaises(ValueError) as contexto:
                    self.g.buscar(id_invalido)
                self.assertNotIsInstance(contexto.exception, TransacaoNaoEncontrada)

    # Validação na edição

    def test_editar_com_tipos_errados_nao_altera_nada(self):
        casos = {
            "descricao numero": {"descricao": 123},
            "valor texto": {"valor": "50"},
            "valor booleano": {"valor": True},
            "categoria numero": {"categoria": 5},
            "data texto": {"data": "2026-04-01"},
        }
        for nome, campos in casos.items():
            with self.subTest(nome):
                with self.assertRaises(ValueError):
                    self.g.editar(self.mercado.id, **campos)
                t = self.g.buscar(self.mercado.id)
                self.assertEqual(
                    (t.descricao, t.valor, t.categoria, t.data),
                    ("Mercado", 100, "mercado", date(2026, 3, 10)),
                )

    def test_editar_com_datetime_guarda_so_a_data(self):
        self.g.editar(self.mercado.id, data=datetime(2026, 4, 1, 15, 30))
        self.assertEqual(self.recarregar().buscar(self.mercado.id).data, date(2026, 4, 1))

    def test_editar_sem_mudancas_nao_regrava_o_arquivo(self):
        with mock.patch.object(self.g, "_salvar") as salvar:
            self.g.editar(self.mercado.id, descricao="Mercado", valor=100, categoria="MERCADO")
        salvar.assert_not_called()


class TestFalhaAoSalvar(unittest.TestCase):
    """Se o arquivo não puder ser gravado, nada deve mudar (nem na memória, nem no disco)."""

    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.arquivo = Path(self.pasta.name) / "transacoes.json"
        self.g = GerenciadorFinanceiro(self.arquivo)
        self.mercado = self.g.adicionar_despesa("Mercado", 100, "mercado", date(2026, 3, 10))
        self.conteudo_original = self.arquivo.read_text(encoding="utf-8")

    def tearDown(self):
        self.pasta.cleanup()

    def disco_falhando(self):
        return mock.patch.object(Path, "replace", side_effect=OSError("disco cheio"))

    def assert_arquivo_intacto(self):
        self.assertEqual(self.arquivo.read_text(encoding="utf-8"), self.conteudo_original)
        self.assertEqual(list(Path(self.pasta.name).glob("*.tmp")), [])

    def test_adicionar_desfaz_se_nao_salvar(self):
        with self.disco_falhando(), self.assertRaises(ErroAoSalvar):
            self.g.adicionar_receita("Salário", 3000, "salário")
        self.assertEqual([t.id for t in self.g.transacoes], [self.mercado.id])
        self.assert_arquivo_intacto()

    def test_editar_desfaz_se_nao_salvar(self):
        with self.disco_falhando(), self.assertRaises(ErroAoSalvar):
            self.g.editar(self.mercado.id, descricao="Feira", valor=50)
        t = self.g.buscar(self.mercado.id)
        self.assertEqual((t.descricao, t.valor), ("Mercado", 100))
        self.assert_arquivo_intacto()

    def test_excluir_desfaz_se_nao_salvar(self):
        with self.disco_falhando(), self.assertRaises(ErroAoSalvar):
            self.g.excluir(self.mercado.id)
        self.assertIs(self.g.buscar(self.mercado.id), self.mercado)
        self.assert_arquivo_intacto()


class TestValorNaoFinito(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.g = GerenciadorFinanceiro(Path(self.pasta.name) / "transacoes.json")

    def tearDown(self):
        self.pasta.cleanup()

    def test_adicionar_rejeita_infinito_e_nan(self):
        for valor in (float("inf"), float("-inf"), float("nan")):
            with self.subTest(valor=valor), self.assertRaises(ValueError):
                self.g.adicionar_despesa("Mercado", valor, "mercado")
        self.assertEqual(self.g.transacoes, [])

    def test_editar_rejeita_infinito(self):
        t = self.g.adicionar_despesa("Mercado", 100, "mercado")
        with self.assertRaises(ValueError):
            self.g.editar(t.id, valor=float("inf"))
        self.assertEqual(self.g.buscar(t.id).valor, 100)


class TestPrecisaoDecimal(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.arquivo = Path(self.pasta.name) / "transacoes.json"
        self.g = GerenciadorFinanceiro(self.arquivo)

    def tearDown(self):
        self.pasta.cleanup()

    def test_soma_sem_erro_de_float(self):
        # Com float, 0.1 + 0.2 dá 0.30000000000000004.
        self.g.adicionar_receita("A", 0.1, "outros")
        self.g.adicionar_receita("B", 0.2, "outros")
        self.assertEqual(self.g.saldo()["receitas"], Decimal("0.30"))

    def test_muitas_somas_pequenas(self):
        for _ in range(100):
            self.g.adicionar_despesa("Café", Decimal("0.10"), "lazer")
        self.assertEqual(self.g.saldo()["despesas"], Decimal("10.00"))

    def test_arredonda_meio_centavo_para_cima(self):
        # round(2.675, 2) com float dá 2.67; aqui o esperado é 2.68.
        t = self.g.adicionar_despesa("Lanche", 2.675, "lazer")
        self.assertEqual(t.valor, Decimal("2.68"))

    def test_valor_que_arredonda_para_zero(self):
        with self.assertRaises(ValueError):
            self.g.adicionar_despesa("Nada", Decimal("0.004"), "outros")

    def test_valores_sao_decimal_apos_recarregar(self):
        self.g.adicionar_receita("Salário", Decimal("3000.50"), "salário")
        recarregado = GerenciadorFinanceiro(self.arquivo)
        self.assertEqual(recarregado.transacoes[0].valor, Decimal("3000.50"))
        self.assertIsInstance(recarregado.saldo()["saldo"], Decimal)


class TestCarregamentoDoArquivo(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.arquivo = Path(self.pasta.name) / "transacoes.json"

    def tearDown(self):
        self.pasta.cleanup()

    def registro(self, **alteracoes) -> dict:
        base = {
            "id": 1,
            "tipo": "despesa",
            "descricao": "Mercado",
            "valor": 100.0,
            "categoria": "mercado",
            "data": "2026-03-10",
        }
        base.update(alteracoes)
        return base

    def escrever(self, conteudo) -> None:
        texto = conteudo if isinstance(conteudo, str) else json.dumps(conteudo)
        self.arquivo.write_text(texto, encoding="utf-8")

    def test_json_corrompido_nao_apaga_o_arquivo(self):
        conteudo = '[{"id": 1, "tipo": "despesa"'
        self.escrever(conteudo)
        with self.assertRaises(ArquivoDeDadosInvalido):
            GerenciadorFinanceiro(self.arquivo)
        self.assertEqual(self.arquivo.read_text(encoding="utf-8"), conteudo)

    def test_json_que_nao_e_lista(self):
        self.escrever({"id": 1})
        with self.assertRaises(ArquivoDeDadosInvalido):
            GerenciadorFinanceiro(self.arquivo)

    def test_registro_valido_carrega(self):
        self.escrever([self.registro()])
        g = GerenciadorFinanceiro(self.arquivo)
        self.assertEqual(g.buscar(1).data, date(2026, 3, 10))

    def test_registros_invalidos(self):
        casos = {
            "campo ausente": {k: v for k, v in self.registro().items() if k != "valor"},
            "id texto": self.registro(id="1"),
            "id booleano": self.registro(id=True),
            "id zero": self.registro(id=0),
            "tipo desconhecido": self.registro(tipo="transferencia"),
            "descricao vazia": self.registro(descricao="  "),
            "descricao numero": self.registro(descricao=123),
            "valor texto": self.registro(valor="abc"),
            "valor com virgula": self.registro(valor="10,50"),
            "valor negativo": self.registro(valor=-5),
            "valor infinito": self.registro(valor=float("inf")),
            "valor nan": self.registro(valor=float("nan")),
            "categoria vazia": self.registro(categoria=""),
            "data invalida": self.registro(data="31/02/2026"),
            "data nula": self.registro(data=None),
            "registro nao objeto": "texto solto",
        }
        for nome, item in casos.items():
            with self.subTest(nome):
                self.escrever([item])
                with self.assertRaises(ArquivoDeDadosInvalido):
                    GerenciadorFinanceiro(self.arquivo)

    def test_arquivo_antigo_com_valor_numerico(self):
        self.escrever([self.registro(valor=99.9)])
        valor = GerenciadorFinanceiro(self.arquivo).buscar(1).valor
        self.assertEqual(valor, Decimal("99.90"))
        self.assertIsInstance(valor, Decimal)

    def test_valor_salvo_como_texto(self):
        g = GerenciadorFinanceiro(self.arquivo)
        g.adicionar_despesa("Mercado", Decimal("99.9"), "mercado")
        dados = json.loads(self.arquivo.read_text(encoding="utf-8"))
        self.assertEqual(dados[0]["valor"], "99.90")

    def test_ids_repetidos(self):
        self.escrever([self.registro(), self.registro(descricao="Feira")])
        with self.assertRaises(ArquivoDeDadosInvalido) as contexto:
            GerenciadorFinanceiro(self.arquivo)
        self.assertIn("repete o ID 1", str(contexto.exception))


if __name__ == "__main__":
    unittest.main()
