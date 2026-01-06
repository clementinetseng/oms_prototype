# OMS Prototype (Backend & Frontend)

這是一個基於 **FastAPI** 開發的 Outlet Management System (OMS) 原型系統，包含獨立的後端 API 與簡易的前端操作介面。

## 🚀 啟動方式

1. 確保已安裝 Python 環境與相依套件。
2. 在終端機執行以下指令啟動伺服器：
   ```bash
   cd oms_prototype
   uvicorn main:app --reload
   ```
3. 開啟瀏覽器訪問：[http://127.0.0.1:8000](http://127.0.0.1:8000)

## 🔑 測試帳號 (Test Accounts)

系統預設建立了以下角色帳號，密碼皆已預先設定：

| 角色 (Role) | 帳號 (Username) | 密碼 (Password) | 權限與功能 |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin` | `admin123` | 最高權限，可管理所有設定 (目前介面導向 Dashboard)。 |
| **Store Manager** | `manager` | `1234` | **店長**。登入後進入 **Dashboard**，可查看營運數據 (Turnover, GGR, BCF)。 |
| **Cashier** | `cashier` | `1234` | **店員**。登入後進入 **POS (Shop Floor)**，負責開台、存款與結算。 |

## 📂 專案結構

- `main.py`: 應用程式入口，包含 API 路由與頁面路由。
- `models.py`: 資料庫模型定義 (SQLAlchemy)。
- `schemas.py`: Pydantic 資料驗證模型。
- `auth.py`: JWT 認證與密碼雜湊處理。
- `database.py`: 資料庫連線設定。
- `seed.py`: 初始化資料庫與建立測試帳號的腳本。
- `templates/`: 前端 HTML 模板 (Login, Dashboard, POS)。
- `oms.db`: SQLite 資料庫檔案 (自動生成)。

## 🛠️ API 文件

啟動伺服器後，可訪問自動生成的 API 文件：
- Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- ReDoc: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
