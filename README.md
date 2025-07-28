# Robô de trading Binance

Este repositório contém os artefatos para o treinamento do robô de trading de criptoativos, que utiliza a [API da Binance](https://developers.binance.com/docs/binance-spot-api-docs).

O repositório está organizado da seguinte maneira:

* `/sql/`: scripts T-SQL para a criação das estruturas de dados.
* `/etl/`: script Python para download e carga dos dados históricos a partir do website da Binance.
* `/ml/`: script Python para criação do modelo de machine learning.
* `/doc/`: assets da documentação.

### Configuração do banco de dados

O ETL realiza a carga dos arquivos CSV extraídos do portal da Binance em um banco de dados SQL Server. Para criar uma instância do SQL Server como desenvolvedor utilizando o Docker, execute:

```
docker run -e "ACCEPT_EULA=Y" -e "MSSQL_SA_PASSWORD=my_super_secret_password" -n sql-server -p 1433:1433 -d --name sql-server mcr.microsoft.com/mssql/server:2022-latest
```

Após a subida da instância, execute o script disponível em `/sql/DDL.sql` para criar os objetos necessários.

![data_structure](/doc/data_structure.png)

### Execução do ETL

O ETL foi desenvolvido em Python 3.11. Para instalar as dependências, execute:

```
pip install -r /etl/requirements.txt
```

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

A criação dos datasets é feita via T-SQL. Neste momento, somente os dados de [k-lines](https://en.wikipedia.org/wiki/Candlestick_chart) são utilizados para tomada de decisão. A lógica utilizada é:

1. Cada dataset é formado por um intervalo de 2 horas de k-lines;
2. Em cada dataset, os primeiros 90 minutos são considerados como dados históricos (passado) e os 30 minutos seguintes como futuro;
3. No 90º minuto, o valor de fechamento é utilizado como valor hipotético de compra; e
4. Se, dentro dos 30 minutos seguintes o valor do ativo ultrapassar o valor de compra acrescido de 3%, a operação é considerada viável (sucesso).

Os scripts estão disponíveis no arquivo `/sql/DML.sql`.

### Machine learning

Optou-se por construir o modelo utilizando a biblioteca [PyTorch](https://pytorch.org/).
