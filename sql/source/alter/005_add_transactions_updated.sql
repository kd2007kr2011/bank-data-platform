-- source.transactions 增加 updated_at，供增量抽取识别变更（可重复执行）。
ALTER TABLE source.transactions
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ
NOT NULL DEFAULT CURRENT_TIMESTAMP;
