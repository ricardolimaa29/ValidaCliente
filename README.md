# ValidaCliente
https://validacliente-demo.streamlit.app/
Protótipo de pré-cadastro regulatório para demonstração.

## Rodar localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Publicar online

Em https://share.streamlit.io/ escolha **New app**, selecione o repositório `ricardolimaa29/ValidaCliente`, branch `main`, arquivo principal `app.py`, e clique em Deploy. Para repositório privado, conceda as permissões solicitadas ao Streamlit.

## Escopo e limitações

- Consulta CNPJ numérico **ao vivo** pela BrasilAPI, sujeita à disponibilidade do serviço.
- AFE, SIVISA, CRF e CRM: links para **conferência manual assistida**. Nenhum desses documentos é automaticamente verificado nesta versão.
- O parecer é preliminar e depende de revisão humana; o aplicativo não grava dados no ERP, não contorna CAPTCHA e não autentica em portais oficiais.
- Não insira dados sigilosos de clientes em demonstrações sem autorização.
