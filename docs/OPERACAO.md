# Operacao

Use somente com consentimento explicito do jogador/cliente.

Fluxo no painel:

1. Acesse `http://YOUR_VPS_IP:18080`.
2. Entre com usuario administrador.
3. Em `Clientes`, crie o cliente e copie o ID completo.
4. Em `Hunts`, envie a Hunt YAML e copie o ID completo da Hunt.
5. Em `Licencas`, crie uma licenca usando o ID do cliente.
6. Na mesma tela de `Licencas`, clique em `Hunts` e informe os IDs completos das Hunts permitidas, separados por virgula.
7. Clique em `Launcher` para baixar o pacote zip daquela licenca.
8. Entregue o pacote ao jogador/cliente autorizado.
9. Depois da execucao, acompanhe `Resultados`, `Maquinas` e `Logs`.

O pacote do launcher contem:

- `launcher.py`
- `requirements.txt`
- `config.json` com a chave de licenca
- `README.txt`

