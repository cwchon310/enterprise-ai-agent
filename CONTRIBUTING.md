# 貢獻指南

歡迎 PR！新功能、bug fix、文件改善都歡迎。

## 開發流程

1. Fork → 建 feature branch
2. `cp .env.example .env` 設定本地變數
3. `pip install -r requirements.txt`
4. `pytest -v` 確保測試通過
5. 提 PR，描述改動與測試結果

## 測試

所有測試用假 LLM，唔使網絡唔使 Key，CI 直接跑。

## License

MIT License。
