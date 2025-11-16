# Secure-Watermark-ID-Document-Generator
一個用於為身份證或其他重要文件影本「燒錄」難以移除且可追溯的**用途綁定浮水印**，並將結果輸出為**扁平化 PDF** 的 Python 命令行工具。

## ✨ 核心功能

* **用途與對象綁定浮水印：** 將指定用途、使用對象、姓名、日期等資訊，以及一個 SHA-256 追溯碼（Token）重複且斜向地繪製在文件上。
* **難以移除的設計：**
    * 浮水印以較高不透明度 (Opacity) 且帶有邊框 (Stroke) 的文字，使其難以透過數位方式去除。
    * 在浮水印上疊加低透明度的**斜線網紋 (Hatch)**，進一步增加修復難度。
    * 最終輸出為**扁平化 (Flat) PDF**，浮水印直接融入像素，無法作為獨立的圖層移除。
* **多格式支援：** 支援單張或多張圖片（如 `.png`, `.jpg`）和多頁 PDF 作為輸入。
* **遮掩功能 (Mask)：** 可指定坐標區域來塗黑或遮掩敏感資訊。
* **PDF 保護：** 可選設置 PDF 開啟密碼 (User Password) 和擁有者密碼 (Owner Password)。

## 🚀 環境需求與安裝

本專案需要 Python 3.8+。

* 步驟一：安裝依賴套件

   使用 `pip` 安裝所需的函式庫：
   
   ```bash
   pip install Pillow pymupdf pikepdf
   ```


* 步驟二：準備字型檔案為確保中文浮水印能正常顯示，請準備一個支援中文的字型檔 (.ttf 或 .otf)。預設路徑為 Windows 的 C:\Windows\Fonts\mingliu.ttc (新細明體)。如果您在其他作業系統或使用不同的字型，請修改程式中的 DEFAULT_FONT_PATH 變數，或是在執行時使用 --font 參數指定。
   * 💡 使用方法基本命令格式Bashpython main.py --input <輸入檔案路徑> --output <輸出檔案路徑> [其他參數]

   範例:
   
   ```bash
   python main.py \
       --input id_card.png \
       --output safe_id_card.pdf \
       --who "xxxx公司" \
       --purpose "僅供XX活動退費使用" \
       --name "<你的名字>" \
       --date "2025-11-16"
   ```
   
   進階功能：遮掩敏感資訊您可以使用 --mask 參數來塗黑指定的矩形區域。格式為 x1,y1,x2,y2（像素坐標）。注意：坐標需要根據您的圖片尺寸手動計算。
   ```bash
   python main.py \
       # ... 其他參數 \
       --mask "400,200,800,300" \
       --mask "100,500,500,600"
   PDF 安全：密碼保護您可以使用 --userpw (開啟密碼) 或 --ownerpw (擁有者密碼，限制列印/修改等權限) 來保護輸出的 PDF。Bashpython main.py \
       # ... 其他參數 \
       --userpw "MyOpenPassword" \
       --ownerpw "MyOwnerPassword"
   ```

## 🛠️ 專案結構.
```
   ├── main.py              # 核心程式碼
   └── README.md            # 本文件
```
