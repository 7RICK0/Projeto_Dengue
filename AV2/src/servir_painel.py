"""Sobe o painel web e mostra um botão para abri-lo em uma página própria.

É usado pela primeira célula de código do notebook. O painel é servido por um servidor local,
que atende só a este computador (ou, no Colab, à sessão de quem está com o notebook aberto).
Nada é publicado na internet nem compartilhado com outras pessoas.
"""

from __future__ import annotations

import html
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

PAGINA = "abrir_painel.html"
TEXTO_DO_BOTAO = "Abrir o painel em uma página própria"

_SERVIDORES: dict[str, ThreadingHTTPServer] = {}

_CAIXA = """\
<div style="font-family:system-ui,-apple-system,'Segoe UI',Roboto,Arial,sans-serif;background:#153746;\
color:#ffffff;border-radius:14px;padding:26px 30px;max-width:780px;margin:8px 0;\
box-shadow:0 4px 14px rgba(0,0,0,.25);">
  <div style="font-size:12px;letter-spacing:.12em;text-transform:uppercase;color:#9fd8c8;font-weight:700;">\
AnteceDengue · Painel interativo</div>
  <div style="font-size:26px;font-weight:800;line-height:1.25;margin:8px 0 6px;">\
Explore a previsão bairro por bairro</div>
  <div style="font-size:15px;line-height:1.5;color:#dbe8ec;margin-bottom:18px;">\
Mapa de risco dos 94 bairros do Recife, previsões das próximas quatro semanas e resultados do modelo, \
com e sem clima.</div>
  <a href="{endereco}" target="_blank" rel="noopener" style="display:inline-block;background:#ffffff;\
color:#153746;font-size:18px;font-weight:800;text-decoration:none;padding:14px 26px;border-radius:10px;">\
{botao} &rarr;</a>
  <div style="font-size:13px;line-height:1.45;color:#b7ccd3;margin-top:14px;">{aviso}</div>
</div>
"""

_AVISO_COLAB = "Abre em uma nova aba. O link é privado: só funciona nesta sessão do Colab, para quem está com este notebook aberto."
_AVISO_LOCAL = "Abre no seu navegador. O painel fica disponível só neste computador, enquanto este notebook estiver aberto."


class _Silencioso(SimpleHTTPRequestHandler):
    def log_message(self, *args) -> None:  # a saída da célula deve conter só o botão
        pass


def iniciar_servidor(pasta: Path) -> ThreadingHTTPServer:
    """Serve a pasta do painel em 127.0.0.1, numa porta livre. Reaproveita o servidor já aberto."""
    chave = str(Path(pasta).resolve())
    if chave not in _SERVIDORES:
        servidor = ThreadingHTTPServer(("127.0.0.1", 0), partial(_Silencioso, directory=chave))
        Thread(target=servidor.serve_forever, daemon=True).start()
        _SERVIDORES[chave] = servidor
    return _SERVIDORES[chave]


def encerrar_servidores() -> None:
    """Fecha os servidores abertos (usado nos testes)."""
    while _SERVIDORES:
        _, servidor = _SERVIDORES.popitem()
        servidor.shutdown()
        servidor.server_close()


def montar_caixa(endereco: str, no_colab: bool) -> str:
    """HTML do botão em destaque que abre o painel."""
    return _CAIXA.format(endereco=html.escape(endereco, quote=True), botao=TEXTO_DO_BOTAO,
                         aviso=_AVISO_COLAB if no_colab else _AVISO_LOCAL)


def _endereco_no_colab(porta: int) -> str:
    from google.colab.output import eval_js

    base = str(eval_js(f"google.colab.kernel.proxyPort({porta})")).rstrip("/")
    return f"{base}/{PAGINA}"


def mostrar_link_do_painel(raiz: Path) -> None:
    """Sobe o painel e mostra, na saída da célula, só o botão que o abre em uma página própria."""
    from IPython.display import HTML, display

    servidor = iniciar_servidor(Path(raiz) / "AV2" / "painel")
    porta = servidor.server_port
    if "google.colab" in sys.modules:
        try:
            endereco, no_colab = _endereco_no_colab(porta), True
        except Exception:
            # Plano B do próprio Colab: ele mostra um link para a mesma página.
            from google.colab import output

            output.serve_kernel_port_as_window(porta, path=f"/{PAGINA}", anchor_text=TEXTO_DO_BOTAO)
            return
    else:
        endereco, no_colab = f"http://127.0.0.1:{porta}/{PAGINA}", False
    display(HTML(montar_caixa(endereco, no_colab)))
