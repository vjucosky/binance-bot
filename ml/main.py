from sqlalchemy import Connection, create_engine, text
from torch.utils.data import Dataset, DataLoader
from settings import DATABASE_SETTINGS
from pandas import read_sql_query


class KLineDataset(Dataset):
    def __init__(self, connection: Connection, name: str, ticks: int, profit: float):
        self.connection = connection
        self.name = name
        self.ticks = ticks
        self.profit = profit

    def __len__(self):
        length = self.connection.execute(text('''
            SELECT MAX(NUMBER) AS NUMBER
            FROM BINANCE_DATASET
            WHERE [NAME] = :name
        '''), {
            'name': self.name
        }).one()[0]

        return length

    def __getitem__(self, index: int):
        dataset = read_sql_query(text('''
            SELECT
                BDK.TRADE_COUNT,
                BDK.OPEN_VALUE,
                BDK.HIGH_VALUE,
                BDK.LOW_VALUE,
                BDK.CLOSE_VALUE,
                BDK.BASE_ASSET_VOLUME,
                BDK.BASE_ASSET_TAKER_BUY_VOLUME,
                BDK.QUOTE_ASSET_VOLUME,
                BDK.QUOTE_ASSET_TAKER_BUY_VOLUME
            FROM BINANCE_DATASET AS BD
            INNER JOIN BINANCE_DATASET_KLINE AS BDK
                ON BD.ID = BDK.DATASET_ID
            WHERE
                BD.[NAME] = :name
                AND BD.NUMBER = :index
                AND BDK.[ROW] > :ticks
            ORDER BY BDK.[ROW]
        '''), connection, params={
            'name': self.name,
            'index': index,
            'ticks': self.ticks
        })

        result = connection.execute(text('''
            SELECT
                MAX(CASE
                    WHEN [SOURCE].[ROW] <= :ticks AND (
                        [SOURCE].OPEN_VALUE >= [TARGET].CLOSE_VALUE * :profit
                        OR [SOURCE].HIGH_VALUE >= [TARGET].CLOSE_VALUE * :profit
                        OR [SOURCE].LOW_VALUE >= [TARGET].CLOSE_VALUE * :profit
                        OR [SOURCE].CLOSE_VALUE >= [TARGET].CLOSE_VALUE * :profit
                    ) THEN 1
                    WHEN [SOURCE].[ROW] <= :ticks THEN 0
                END) AS IS_PROFITABLE
            FROM BINANCE_DATASET AS BD
            INNER JOIN BINANCE_DATASET_KLINE AS [SOURCE]
                ON BD.ID = [SOURCE].DATASET_ID
            INNER JOIN BINANCE_DATASET_KLINE AS [TARGET]
                ON BD.ID = [TARGET].DATASET_ID
            WHERE
                BD.[NAME] = :name
                AND BD.NUMBER = :index
                AND [TARGET].[ROW] = :ticks + 1
        '''), {
            'name': self.name,
            'index': index,
            'ticks': self.ticks,
            'profit': self.profit
        }).one()[0]

        return dataset.to_numpy(), result


if __name__ == '__main__':
    engine = create_engine(**DATABASE_SETTINGS)

    connection = engine.connect()

    kline_dataset = KLineDataset(connection)

    dataloader = DataLoader(kline_dataset)
