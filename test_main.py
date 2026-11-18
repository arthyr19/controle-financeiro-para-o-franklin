import unittest
from decimal import Decimal
from unittest import mock

from main import ler_valor, normalizar_valor


class TestLeituraDeValor(unittest.TestCase):
    def test_formatos_aceitos(self):
        casos = {
            "1.500": "1500",
            "2.000": "2000",
            "1.234.567": "1234567",
            "1.500,00": "1500.00",
            "1.234,56": "1234.56",
            "1234,56": "1234.56",
            "1234.56": "1234.56",
            "10.5": "10.5",
            "150": "150",
            "R$ 1.500": "1500",
        }
        for entrada, esperado in casos.items():
            with self.subTest(entrada=entrada):
                self.assertEqual(normalizar_valor(entrada), esperado)

    def test_ponto_de_milhar_no_menu(self):
        #antes, "3.000" era registrado como RS 3,00
        with mock.patch("builtins.input", return_value="3.000"):
            self.assertEqual(ler_valor("Valor: "), Decimal("3000.00"))
        
    def test_enter_vazio_quando_opcional(self):
        with mock.patch("builtins.input", return_value=""):
            self.assertIsNone(ler_valor("Valor: ", obrigatorio=False))


if __name__ == "__main__":
    unittest.main()
