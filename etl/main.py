import requests


from settings import DATABASE_SETTINGS, STAGE_FOLDER, ARCHIVE_FOLDER
from sqlalchemy import Engine, create_engine, text
from datetime import datetime, timedelta
from argparse import ArgumentParser
from calendar import monthrange
from zipfile import ZipFile
from pandas import read_csv
from io import BytesIO


def sync_symbol_data(engine: Engine):
    print(f'Downloading symbol data')

    request = requests.get('https://api.binance.com/api/v3/exchangeInfo')

    data = request.json()

    with engine.connect() as connection:
        for symbol in data['symbols']:
            connection.execute(text('''
                SET NOCOUNT ON

                IF NOT EXISTS(
                    SELECT 1
                    FROM SYMBOL
                    WHERE [NAME] = :name
                )
                BEGIN
                    INSERT INTO SYMBOL (
                        [NAME],
                        BASE_ASSET_NAME,
                        BASE_ASSET_PRECISION,
                        QUOTE_ASSET_NAME,
                        QUOTE_ASSET_PRECISION,
                        IS_ICEBERG_ALLOWED,
                        IS_OCO_ALLOWED,
                        IS_SPOT_TRADING_ALLOWED,
                        IS_MARGIN_TRADING_ALLOWED
                    )
                    VALUES (
                        :name,
                        :base_asset_name,
                        :base_asset_precision,
                        :quote_asset_name,
                        :quote_asset_precision,
                        :is_iceberg_allowed,
                        :is_oco_allowed,
                        :is_spot_trading_allowed,
                        :is_margin_trading_allowed
                    )
                END
                ELSE
                BEGIN
                    UPDATE SYMBOL
                    SET
                        BASE_ASSET_NAME = :base_asset_name,
                        BASE_ASSET_PRECISION = :base_asset_precision,
                        QUOTE_ASSET_NAME = :quote_asset_name,
                        QUOTE_ASSET_PRECISION = :quote_asset_precision,
                        IS_ICEBERG_ALLOWED = :is_iceberg_allowed,
                        IS_OCO_ALLOWED = :is_oco_allowed,
                        IS_SPOT_TRADING_ALLOWED = :is_spot_trading_allowed,
                        IS_MARGIN_TRADING_ALLOWED = :is_margin_trading_allowed,
                        UPDATED_AT = GETDATE()
                    WHERE [NAME] = :name
                END
            '''), {
                'name': symbol['symbol'],
                'base_asset_name': symbol['baseAsset'],
                'base_asset_precision': symbol['baseAssetPrecision'],
                'quote_asset_name': symbol['quoteAsset'],
                'quote_asset_precision': symbol['quoteAssetPrecision'],
                'is_iceberg_allowed': symbol['icebergAllowed'],
                'is_oco_allowed': symbol['ocoAllowed'],
                'is_spot_trading_allowed': symbol['isSpotTradingAllowed'],
                'is_margin_trading_allowed': symbol['isMarginTradingAllowed']
            })

            connection.commit()


def load_kline_historical_data(engine: Engine, name: str, year: int, month: int):
    with engine.connect() as connection:
        symbol_id = connection.execute(text('''
            SELECT ID
            FROM SYMBOL
            WHERE [NAME] = :name
        '''), {
            'name': name
        }).one()[0]

    print(f'Downloading historical data for symbol {name} (ID {symbol_id}), period {month:02d}-{year}')

    request = requests.get(f'https://data.binance.vision/data/spot/monthly/klines/{name}/1m/{name}-1m-{year}-{month:02d}.zip')

    with ZipFile(BytesIO(request.content)) as archive:
        archive.extractall(STAGE_FOLDER)

    for file in STAGE_FOLDER.rglob('*.csv'):
        print(f'Loading file {file.name}')

        data = file.open(encoding='UTF-8')

        dataframe = read_csv(data, delimiter=',', header=None, names=['open_timestamp', 'open_value', 'high_value', 'low_value', 'close_value', 'base_asset_volume', 'close_timestamp', 'quote_asset_volume', 'trade_count', 'base_asset_taker_buy_volume', 'quote_asset_taker_buy_volume'], index_col=False, decimal='.')

        dataframe['SYMBOL_ID'] = symbol_id

        with engine.connect() as connection:
            dataframe.to_sql('SYMBOL_KLINE', connection, if_exists='append', index=False, chunksize=10000)

            connection.commit()

        data.close()

    file.rename(ARCHIVE_FOLDER / file.name)


if __name__ == '__main__':
    parser = ArgumentParser()

    parser.add_argument('-n', '--name', action='extend', nargs='+', required=True)
    parser.add_argument('-s', '--start', type=lambda x: datetime.strptime(x, '%m-%Y'), required=True)
    parser.add_argument('-e', '--end', type=lambda x: datetime.strptime(x, '%m-%Y'), required=True)

    args = parser.parse_args()

    periods = [args.start, ]

    while True:
        period = periods[-1] + timedelta(days=monthrange(periods[-1].year, periods[-1].month)[1])

        if period <= args.end:
            periods.append(period)
        else:
            break

    engine = create_engine(**DATABASE_SETTINGS)

    sync_symbol_data(engine)

    for name in args.name:
        for period in periods:
            load_kline_historical_data(engine, name, period.year, period.month)
