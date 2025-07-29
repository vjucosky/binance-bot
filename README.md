# Robô de trading Binance

Este repositório contém os artefatos para o treinamento do robô de trading de criptoativos, que utiliza a [API da Binance](https://developers.binance.com/docs/binance-spot-api-docs).

O repositório está organizado da seguinte maneira:

* `/sql/`: scripts T-SQL para a criação das estruturas de dados.
* `/etl/`: script Python para download e carga dos dados históricos a partir do website da Binance.
* `/ml/`: script Python para criação do modelo de machine learning.
* `/bot/`: robô de trading, desenvolvido em Python.
* `/doc/`: assets da documentação.

Todos os scripts foram desenvolvidos em Python 3.11. Para instalar as dependências, execute:

```
pip install -r requirements.txt
```

### Configuração do banco de dados

O ETL realiza a carga dos arquivos CSV extraídos do portal da Binance em um banco de dados SQL Server. Para criar uma instância do SQL Server como desenvolvedor utilizando o Docker, execute:

```
docker run -e "ACCEPT_EULA=Y" -e "MSSQL_SA_PASSWORD=my_super_secret_password" -n sql-server -p 1433:1433 -d --name sql-server mcr.microsoft.com/mssql/server:2022-latest
```

Após a subida da instância, execute o script disponível em `/sql/DDL.sql` para criar os objetos necessários.

![data_structure](/doc/data_structure.png)

### Execução do ETL

Antes de iniciar o ETL, atualize o arquivo `/etl/.env` com as credenciais do banco de dados criado anteriormente. A execução se dá via linha de comando utilizando o arquivo `/etl/main.py`. Os argumentos necessários são:

* `--name`: nome(s) do(s) par(es) a baixar.
* `--start`: período inicial a utilizar (incluído), no formato `MM-AAAA`.
* `--end`: período final a utilizar (incluído), no formato `MM-AAAA`.

Por exemplo, para baixar os dados históricos dos pares ETH/BTC e LTC/BTC do período de 01/2020 a 12/2020, utilize o seguinte comando:

```
--name ETHBTC LTCBTC --start 01-2020 --end 12-2020
```

A cada execução, a tabela `BINANCE_SYMBOL` é atualizada com todos os pares disponíveis no catálogo da Binance.

Os arquivos baixados são salvos temporariamente na pasta `/etl/stage/` e, conforme são carregados para o banco de dados, são movidos para a pasta `/etl/archive/`.

### Criação dos datasets

A criação dos datasets é feita via T-SQL. Neste momento, somente os dados de [klines](https://en.wikipedia.org/wiki/Candlestick_chart) são utilizados para tomada de decisão. A lógica utilizada é:

1. Cada dataset é formado por um intervalo de 2 horas de klines;
2. Em cada dataset, os primeiros 90 minutos são considerados como dados históricos (passado) e os 30 minutos seguintes como futuro;
3. No 90º minuto, o valor de fechamento é utilizado como valor hipotético de compra; e
4. Se, dentro dos 30 minutos seguintes o valor do ativo ultrapassar o valor de compra acrescido de 3%, a operação é considerada viável (sucesso).

Os datasets gerados são utilizados para treinamento do robô utilizando técnicas de machine learning.

Os scripts estão disponíveis no arquivo `/sql/DML.sql`.

### Execução do robô

Antes de iniciar o robô, atualize o arquivo `/bot/.env` com as credenciais do banco de dados criado anteriormente e suas [chaves para a API da Binance](https://www.binance.com/pt-BR/support/faq/detail/6b9a63f1e3384cf48a2eedb82767a69a).

> [!IMPORTANT]
> O robô utiliza websockets para monitorar o status das transações. Por causa disso, a única forma de autenticação suportada é por chave privada Ed25519. Certifique-se de habilitar as permissões para leitura e trading spot.

Além de ouvir por atualizações nas ordens, o robô executa a seguinte lógica a cada minuto:

1. Obter um dataset contendo os últimos 90 minutos de klines (completos);
2. Passar o dataset pelo modelo de machine learning desenvolvido anteriormente; e
3. Em caso de previsão de lucro nos próximos 30 minutos, é colocada uma ordem para compra.

Caso a compra seja bem-sucedida, automaticamente é colocada uma ordem de venda respeitando os 3% de margem de lucro estipulados durante o treinamento. O robô não realiza nenhuma outra operação até que a ordem de venda seja liquidada.
