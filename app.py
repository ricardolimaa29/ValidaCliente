import streamlit as st
import requests, re, json
from datetime import datetime, timezone

st.set_page_config(page_title="ValidaCliente | MVP", page_icon="🧾", layout="wide")
st.title("ValidaCliente")
st.caption("Protótipo de pré-cadastro • Fontes cadastrais BrasilAPI / CNPJ.ws • Conferência regulatória assistida")
st.info("Somente o CNPJ é consultado automaticamente. AFE, SIVISA, CRF e CRM exigem conferência nos portais competentes. 'Não verificado' não significa 'irregular'.")

PORTAIS = {
    "AFE / Anvisa": "https://consultas.anvisa.gov.br/#/empresas/empresas/",
    "SIVISA / São Paulo": "https://sivisa.saude.sp.gov.br/",
    "CRF / Conselho de Farmácia": "https://www.cff.org.br/",
    "CRM / Conselho de Medicina": "https://portal.cfm.org.br/busca-medicos/",
}
def normalizar(value):
    return re.sub(r"\D", "", value)
def cnpj_valido(value):
    if len(value) != 14 or len(set(value)) == 1:
        return False
    nums = list(map(int, value))
    for length, weights in [(12, [5,4,3,2,9,8,7,6,5,4,3,2]), (13, [6,5,4,3,2,9,8,7,6,5,4,3,2])]:
        digit = (sum(a*b for a,b in zip(nums[:length], weights))*10)%11
        if digit == 10: digit = 0
        if nums[length] != digit: return False
    return True

with st.form("consulta"):
    entrada = st.text_input("CNPJ", placeholder="00.000.000/0000-00")
    buscar = st.form_submit_button("Consultar CNPJ", type="primary")
def consultar(cnpj):
    erros = []
    fontes = [
        ("BrasilAPI", f"https://brasilapi.com.br/api/cnpj/v1/{cnpj}"),
        ("CNPJ.ws", f"https://publica.cnpj.ws/cnpj/{cnpj}"),
    ]
    for nome, url in fontes:
        try:
            resposta = requests.get(url, timeout=18, headers={"Accept": "application/json", "User-Agent": "ValidaCliente-MVP/0.2"})
            if resposta.status_code != 200:
                erros.append(f"{nome}: HTTP {resposta.status_code}")
                continue
            dados = resposta.json()
            if nome == "CNPJ.ws":
                est = dados.get("estabelecimento") or {}
                atividade = est.get("atividade_principal") or {}
                situacao = est.get("situacao_cadastral") or {}
                dados = {
                    "razao_social": dados.get("razao_social"),
                    "nome_fantasia": est.get("nome_fantasia"),
                    "descricao_situacao_cadastral": situacao.get("descricao") if isinstance(situacao, dict) else str(situacao),
                    "uf": (est.get("estado") or {}).get("sigla") if isinstance(est.get("estado"), dict) else est.get("estado"),
                    "logradouro": est.get("logradouro"), "numero": est.get("numero"),
                    "bairro": est.get("bairro"),
                    "municipio": (est.get("cidade") or {}).get("nome") if isinstance(est.get("cidade"), dict) else est.get("cidade"),
                    "cnae_fiscal_descricao": atividade.get("descricao") if isinstance(atividade, dict) else "",
                }
            if not dados.get("razao_social"):
                erros.append(f"{nome}: resposta sem razão social")
                continue
            return dados, nome, erros
        except (requests.RequestException, ValueError) as exc:
            erros.append(f"{nome}: {type(exc).__name__}")
    return None, None, erros

if buscar:
    st.session_state.pop("empresa", None)
    st.session_state.pop("fonte", None)
    cnpj = normalizar(entrada)
    if not cnpj_valido(cnpj):
        st.error("CNPJ numérico inválido. Este MVP valida CNPJ numérico.")
    else:
        with st.spinner("Consultando fontes cadastrais..."):
            dados, fonte, erros = consultar(cnpj)
        if dados:
            st.session_state["empresa"] = dados
            st.session_state["cnpj"] = cnpj
            st.session_state["fonte"] = fonte
            st.success(f"Consulta cadastral concluída via {fonte}.")
        else:
            st.error("Não foi possível obter os dados cadastrais. Isso NÃO significa que o CNPJ inexista ou esteja regular.")
            st.code("\\n".join(erros))
            st.caption("HTTP 404: cadastro não retornado pela fonte; 429: limite de requisições; 5xx: falha do serviço. Consulte também o comprovante oficial da Receita Federal.")
            st.link_button("Consulta oficial de CNPJ", "https://www.gov.br/pt-br/servicos/consultar-cadastro-nacional-de-pessoas-juridicas")
if "empresa" in st.session_state:
    empresa = st.session_state["empresa"]
    cnpj = st.session_state["cnpj"]
    st.subheader(empresa.get("razao_social") or "Empresa consultada")
    a,b,c = st.columns(3)
    a.metric("CNPJ", cnpj)
    situacao = empresa.get("descricao_situacao_cadastral") or "Não informada"
    b.metric("Situação cadastral", situacao)
    c.metric("UF", empresa.get("uf") or "—")
    st.write("**Nome fantasia:**", empresa.get("nome_fantasia") or "Não informado")
    st.write("**Endereço:**", ", ".join(str(empresa.get(k) or "") for k in ("logradouro","numero","bairro","municipio","uf") if empresa.get(k)))
    st.write("**CNAE principal:**", empresa.get("cnae_fiscal_descricao") or "Não informado")
    st.caption(f"Fonte cadastral: {st.session_state.get('fonte', 'não informada')}. Não é consulta de dívidas; confirme os dados na Receita Federal.")
    st.error("CNPJ ativo não comprova ausência de dívidas ou autorização para vender. Regularidade fiscal e situação financeira: NÃO CONSULTADAS automaticamente.")
    st.markdown("[Consultar certidões RFB/PGFN](https://www.gov.br/pt-br/servicos/consultar-certidoes-emitidas-pela-receita-federal-e-ou-procuradoria-geral-da-fazenda-nacional) · [Emitir certidão fiscal](https://www.gov.br/pt-br/servicos/emitir-certidao-de-regularidade-fiscal) · [Lista de devedores PGFN](https://www.gov.br/pt-br/servicos/consultar-lista-de-devedores-da-pgfn)")
    st.subheader("Conferência fiscal e financeira")
    fiscal = st.selectbox("Certidão RFB/PGFN (conferência humana)", ["Não verificado", "CND — negativa", "CPEND — positiva com efeitos de negativa", "CPD — positiva", "Emissão indisponível / inconclusiva"], key=f"fiscal_{cnpj}")
    interno = st.selectbox("Débitos ou bloqueios no ERP (conferência humana)", ["Não verificado", "Sem bloqueio confirmado", "Com débito ou bloqueio confirmado"], key=f"interno_{cnpj}")
    st.caption("CPEND pode coexistir com dívidas suspensas ou parceladas. A certidão não substitui a análise de crédito.")
    st.divider()
    st.subheader("Checklist regulatório")
    st.caption("CRF é Farmácia; CRM é Medicina. Confirme quais registros a empresa exige para este tipo de cliente.")
    status = {}
    for nome, link in PORTAIS.items():
        with st.expander(nome):
            st.link_button("Abrir portal", link)
            status[nome] = st.selectbox("Conferência", ["Não verificado", "Regular (conferido)", "Pendente / irregular (conferido)", "Não se aplica (justificado)"], key=f"status_{nome}_{cnpj}")
            st.text_input("Número / observação", key=f"obs_{nome}_{cnpj}")
    if situacao.upper() != "ATIVA":
        parecer = "REVISÃO NECESSÁRIA — CNPJ não confirmado como ativo"
        st.warning(parecer)
    elif fiscal == "CPD — positiva" or interno == "Com débito ou bloqueio confirmado" or any(s.startswith("Pendente") for s in status.values()):
        parecer = "NÃO LIBERAR — há pendência registrada"
        st.error(parecer)
    elif fiscal in ("Não verificado", "Emissão indisponível / inconclusiva") or interno == "Não verificado" or any(s == "Não verificado" for s in status.values()):
        parecer = "AGUARDANDO CONFERÊNCIA — não liberar automaticamente"
        st.warning(parecer)
    else:
        parecer = "PRONTO PARA ANÁLISE HUMANA — checklist preenchido"
        st.success(parecer)
    registro = {
        "consultado_em": datetime.now(timezone.utc).isoformat(),
        "cnpj": cnpj,
        "empresa": empresa,
        "documentos": {nome: {"status": valor, "observacao": st.session_state.get(f"obs_{nome}_{cnpj}", ""), "portal": PORTAIS[nome]} for nome,valor in status.items()},
        "certidao_fiscal_declarada": fiscal,
        "situacao_erp_declarada": interno,
        "parecer_preliminar": parecer
    }
    st.download_button("Baixar relatório JSON", json.dumps(registro, ensure_ascii=False, indent=2), file_name=f"consulta_{cnpj}.json", mime="application/json")
    st.caption("Este MVP não cadastra no ERP, não contorna CAPTCHA e não emite aprovação regulatória.")
