import streamlit as st
import requests, re, json
from datetime import datetime, timezone

st.set_page_config(page_title="ValidaCliente | MVP", page_icon="🧾", layout="wide")
st.title("ValidaCliente")
st.caption("Protótipo de pré-cadastro • Consulta real de CNPJ via BrasilAPI • Conferência regulatória assistida")
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
if buscar:
    cnpj = normalizar(entrada)
    if not cnpj_valido(cnpj):
        st.error("CNPJ numérico inválido. Este MVP valida CNPJ numérico.")
    else:
        try:
            with st.spinner("Consultando fonte cadastral..."):
                resposta = requests.get(f"https://brasilapi.com.br/api/cnpj/v1/{cnpj}", timeout=20)
                resposta.raise_for_status()
                st.session_state["empresa"] = resposta.json()
                st.session_state["cnpj"] = cnpj
        except requests.RequestException:
            st.error("A consulta não pôde ser concluída. Tente novamente mais tarde; nenhuma regularidade foi presumida.")
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
    st.caption("Consulta por BrasilAPI; confirme a situação na fonte oficial quando necessário.")
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
    elif any(s.startswith("Pendente") for s in status.values()):
        parecer = "NÃO LIBERAR — há pendência registrada"
        st.error(parecer)
    elif any(s == "Não verificado" for s in status.values()):
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
        "parecer_preliminar": parecer
    }
    st.download_button("Baixar relatório JSON", json.dumps(registro, ensure_ascii=False, indent=2), file_name=f"consulta_{cnpj}.json", mime="application/json")
    st.caption("Este MVP não cadastra no ERP, não contorna CAPTCHA e não emite aprovação regulatória.")
