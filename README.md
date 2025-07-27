# Robô de trading Binance

Este repositório contém os artefatos necessários para o treinamento do robô de trading de criptoativos, que utiliza a [API da Binance](https://developers.binance.com/docs/binance-spot-api-docs).

O repositório está organizado da seguinte maneira:

* `/sql/`: scripts T-SQL para a criação do banco de dados e das tabelas necessárias.
* `/etl/`: script Python para download e carga dos dados a partir do website da Binance.
* `/doc/`: assets da documentação.

### Configuração do banco de dados

O ETL realiza a carga dos arquivos CSV extraídos do portal da Binance em um banco de dados SQL Server. Para criar uma instância do SQL Server como desenvolvedor utilizando o Docker, execute:

```
docker run -e "ACCEPT_EULA=Y" -e "MSSQL_SA_PASSWORD=my_super_secret_password" -n sql-server -p 1433:1433 -d --name sql-server mcr.microsoft.com/mssql/server:2022-latest
```

Após a subida da instância, execute o script disponível em `/sql/DDL.sql` para criar o banco de dados e as tabelas necessárias.

### Execução do ETL

O ETL foi desenvolvido em Python 3.11. Para instalar as dependências necessárias, execute:

```
pip install -r /etl/requirements.txt
```

Antes de iniciar o ETL, atualize o arquivo `/etl/.env` com as credenciais do banco de dados criado anteriormente. A execução se dá via linha de comando utilizando o arquivo `/etl/main.py`. Os argumentos suportados ao baixar os dados históricos são:

* `--name`: nome(s) do(s) par(es) a baixar.
* `--start`: período inicial a utilizar (incluído), no formato `MM-AAAA`.
* `--end`: período final a utilizar (incluído), no formato `MM-AAAA`.

Por exemplo, para baixar os dados históricos dos pares ETH/BTC e LTC/BTC do período de 01/2020 a 12/2020, utilize o seguinte comando:

```
--name ETHBTC LTCBTC --start 01-2020 --end 12-2020
```

A cada execução, a tabela `SYMBOL` é atualizada com todos os pares disponíveis no catálogo da Binance.

Os arquivos baixados são salvos temporariamente na pasta `/etl/stage/` e, conforme são carregados para o banco de dados, são movidos para a pasta `/etl/archive/`.
