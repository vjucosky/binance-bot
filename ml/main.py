from sqlalchemy import Connection, create_engine, text
from torch.utils.data import Dataset, DataLoader
from settings import DATABASE_SETTINGS
from pandas import read_sql_query


class KLineDataset(Dataset):
    def __init__(self, connection: Connection):
        self.connection = connection

    def __len__(self):
        length = self.connection.execute(text('''
            SELECT MAX(DATASET_NUMBER) AS DATASET_LENGTH
            FROM BINANCE_DATASET_KLINE
        ''')).one()[0]

        return length

    def __getitem__(self, index: int):
        dataset = read_sql_query(text('''
            DECLARE @CURRENT_TICK AS int = 31

            SELECT
                TRADE_COUNT,
                OPEN_VALUE,
                HIGH_VALUE,
                LOW_VALUE,
                CLOSE_VALUE,
                BASE_ASSET_VOLUME,
                BASE_ASSET_TAKER_BUY_VOLUME,
                QUOTE_ASSET_VOLUME,
                QUOTE_ASSET_TAKER_BUY_VOLUME
            FROM BINANCE_DATASET_KLINE
            WHERE
                DATASET_NUMBER = :index
                AND DATASET_ROW >= @CURRENT_TICK
            ORDER BY DATASET_ROW
        '''), connection, params={
            'index': index
        })

        result = connection.execute(text('''
            DECLARE @PROFIT_MARGIN AS decimal(18, 8) = 1.03
            DECLARE @CURRENT_TICK AS int = 31

            SELECT
                MAX(CASE
                    WHEN [SOURCE].DATASET_ROW < @CURRENT_TICK AND (
                        [SOURCE].OPEN_VALUE >= [TARGET].CLOSE_VALUE * @PROFIT_MARGIN
                        OR [SOURCE].HIGH_VALUE >= [TARGET].CLOSE_VALUE * @PROFIT_MARGIN
                        OR [SOURCE].LOW_VALUE >= [TARGET].CLOSE_VALUE * @PROFIT_MARGIN
                        OR [SOURCE].CLOSE_VALUE >= [TARGET].CLOSE_VALUE * @PROFIT_MARGIN
                    ) THEN 1
                    WHEN [SOURCE].DATASET_ROW < @CURRENT_TICK THEN 0
                END) AS IS_PROFITABLE
            FROM BINANCE_DATASET_KLINE AS [SOURCE]
            INNER JOIN BINANCE_DATASET_KLINE AS [TARGET]
                ON
                    [SOURCE].DATASET_NUMBER = [TARGET].DATASET_NUMBER
                    AND [TARGET].DATASET_ROW = @CURRENT_TICK
            WHERE [SOURCE].DATASET_NUMBER = :index
            GROUP BY [SOURCE].DATASET_NUMBER
        '''), {
            'index': index
        }).one()[0]

        return dataset.to_numpy(), result


if __name__ == '__main__':
    engine = create_engine(**DATABASE_SETTINGS)

    connection = engine.connect()

    kline_dataset = KLineDataset(connection)

    dataloader = DataLoader(kline_dataset)
