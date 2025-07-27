from sqlalchemy import Connection, create_engine, text
from torch.utils.data import Dataset, DataLoader
from settings import DATABASE_SETTINGS
from pandas import read_sql_query


class KLineDataset(Dataset):
    def __init__(self, connection: Connection):
        self.connection = connection

        self.dataframe = read_sql_query(text('''
            DECLARE @PROFIT_MARGIN AS decimal(18, 8) = 1.03 -- 3% de margem de lucro
            DECLARE @CURRENT_TICK AS int = 31;              -- A 31ª linha de cada dataset é considerada como o momento atual; as linhas 1-30 são consideradas como futuro

            SELECT
                BDK.ID,
                BDK.DATASET_NUMBER,
                BDK.DATASET_ROW,
                BDK.TRADE_COUNT,
                BDK.OPEN_VALUE,
                BDK.HIGH_VALUE,
                BDK.LOW_VALUE,
                BDK.CLOSE_VALUE,
                BDK.BASE_ASSET_VOLUME,
                BDK.BASE_ASSET_TAKER_BUY_VOLUME,
                BDK.QUOTE_ASSET_VOLUME,
                BDK.QUOTE_ASSET_TAKER_BUY_VOLUME,
                BDK.OPEN_TIMESTAMP,
                BDK.CLOSE_TIMESTAMP,
                [TARGET].TARGET_SELL_VALUE,
                [TARGET].IS_PROFITABLE
            FROM BINANCE_DATASET_KLINE AS BDK
            INNER JOIN (
                SELECT
                    DATASET_NUMBER,
                    MAX(TARGET_SELL_VALUE) AS TARGET_SELL_VALUE,
                    CAST(MAX(IS_PROFITABLE) AS bit) AS IS_PROFITABLE
                FROM (
                    SELECT
                        [SOURCE].DATASET_NUMBER,
                        [SOURCE].DATASET_ROW,
                        IIF([SOURCE].DATASET_ROW = @CURRENT_TICK, [TARGET].CLOSE_VALUE * @PROFIT_MARGIN, NULL) AS TARGET_SELL_VALUE,
                        CASE
                            WHEN [SOURCE].DATASET_ROW < @CURRENT_TICK AND (
                                [SOURCE].OPEN_VALUE >= [TARGET].CLOSE_VALUE * @PROFIT_MARGIN
                                OR [SOURCE].HIGH_VALUE >= [TARGET].CLOSE_VALUE * @PROFIT_MARGIN
                                OR [SOURCE].LOW_VALUE >= [TARGET].CLOSE_VALUE * @PROFIT_MARGIN
                                OR [SOURCE].CLOSE_VALUE >= [TARGET].CLOSE_VALUE * @PROFIT_MARGIN
                            ) THEN 1
                            WHEN [SOURCE].DATASET_ROW < @CURRENT_TICK THEN 0
                        END AS IS_PROFITABLE
                    FROM BINANCE_DATASET_KLINE AS [SOURCE]
                    LEFT JOIN BINANCE_DATASET_KLINE AS [TARGET]
                        ON
                            [SOURCE].DATASET_NUMBER = [TARGET].DATASET_NUMBER
                            AND [TARGET].DATASET_ROW = @CURRENT_TICK
                ) AS S
                GROUP BY DATASET_NUMBER
                HAVING COUNT(*) = 120
            ) AS [TARGET]
                ON BDK.DATASET_NUMBER = [TARGET].DATASET_NUMBER
            WHERE BDK.DATASET_ROW >= @CURRENT_TICK
            ORDER BY
                BDK.DATASET_NUMBER,
                BDK.DATASET_ROW
        '''), connection)

    def __len__(self):
        return int(len(self.dataframe) / 90)

    def __getitem__(self, index: int):
        dataset = self.dataframe.iloc[index * 90:index * 90 + 90, 3:12]

        label = self.dataframe.iloc[index * 90]['IS_PROFITABLE'].astype(int)

        return dataset.to_numpy(), label


if __name__ == '__main__':
    engine = create_engine(**DATABASE_SETTINGS)

    connection = engine.connect()

    kline_dataset = KLineDataset(connection)

    dataloader = DataLoader(kline_dataset)
