

##  Como usar / executar  

1. Clone este repositório:  

   git clone https://github.com/CodeTigs/Projeto_FInal_Fuzzy.git

2. Certifique-se de ter Python instalado (versão 3.10.2).  
3. (Opcional) Instale dependências, se houver — neste caso não há bibliotecas externas; o código puro deve rodar diretamente.  
4. Execute:  

   Isso irá rodar o controlador e gerar os gráficos de resultados.  

5. Abra os gráficos (.png) ou o arquivo `index.html` para visualizar os resultados.  

##  O que o controlador faz  

- Recebe como entrada o erro e a variação do erro.  
- Aplica fuzzificação e uma base de regras fuzzy (heurísticas) para determinar a ação de controle.  
- Sai pela defuzzificação (centro de gravidade) uma saída contínua de controle.  
- Permite avaliar a resposta do sistema a diferentes cenários (setpoint, ruído, perturbações).  

##  Exemplos / Cenários de Teste  

- Degrau pequeno ou grande no setpoint — observe tempo de estabilização, overshoot, erro permanente.  
- Perturbações súbitas — verifique robustez e recuperação.  
- Ruído no sinal de entrada — avalie estabilidade e suavidade da saída.  

##  Resultados e Comparações  

Nos testes realizados, o controlador fuzzy demonstrou:  
- Resposta rápida e estável;  
- Baixo overshoot;  
- Robustez a ruído e perturbações;  
- Comportamento mais suave e resiliente comparado a controladores clássicos (P/PID).  

##  Possíveis melhorias / extensões  

- Adicionar implementação de controlador tradicional (PID) para comparação automática.  
- Permitir configuração externa das funções de pertinência e base de regras.  
- Gerar análises automatizadas com múltiplos cenários e saída de dados/tabulação.  
- Adicionar documentação técnica completa (design de fuzzy, regras, diagramas, análise de resultados).  

##  Referências / Motivação  

Este projeto tem como base os conceitos de lógica fuzzy e controle adaptativo, buscando demonstrar vantagens da abordagem fuzzy em sistemas não-lineares ou com incertezas.  

##  Autor  
- Desenvolvido por Tiago Rodrigue e Gabriel Bissacot.  
