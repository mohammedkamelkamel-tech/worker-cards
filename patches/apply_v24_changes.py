#!/usr/bin/env python3
from pathlib import Path
import re, sys

root = Path(sys.argv[1])
main = root / "app/src/main/java/com/example/workercards/MainActivity.java"
paths = root / "app/src/main/res/xml/file_paths.xml"
s = main.read_text(encoding="utf-8")

price_line = re.compile(r'(?m)^(\s*this\.price\s*=\s*)[^;]+;[^\n]*$')
if 'this.price = salePriceForDenomination(denomination);' not in s:
    s, count = price_line.subn(r'\1salePriceForDenomination(denomination); // سعر البيع الفعلي للفئة', s, count=1)
    if count != 1:
        raise SystemExit("Cannot locate InvoiceRow price assignment; refusing to patch unknown source.")

helper = '''    private static int salePriceForDenomination(int denomination) {
        switch (denomination) {
            case 100: return 85;
            case 200: return 180;
            case 250: return 225;
            case 500: return 450;
            default: return denomination;
        }
    }

'''
if 'private static int salePriceForDenomination' not in s:
    marker = '    @Override\n    protected void onCreate(Bundle savedInstanceState) {'
    if marker not in s:
        raise SystemExit("Cannot locate onCreate insertion point.")
    s = s.replace(marker, helper + marker, 1)

if 'import android.graphics.pdf.PdfDocument;' not in s:
    s = s.replace('import android.graphics.RectF;', 'import android.graphics.RectF;\nimport android.graphics.pdf.PdfDocument;')
if 'import android.os.Environment;' not in s:
    s = s.replace('import android.os.Bundle;', 'import android.os.Bundle;\nimport android.os.Environment;')

s = s.replace('denomColor = 0xFFD97706; // Amber/Gold\n                        denomBg = 0xFFFFFBEB;',
              'denomColor = 0xFF0284C7; // Sky blue\n                        denomBg = 0xFFE0F2FE;')

share_pattern = re.compile(r'\s*File dir = new File\(getCacheDir\(\), "reports"\);.*?Uri uri = FileProvider\.getUriForFile\(this, "([^"]+)", file\);', re.S)
share_match = share_pattern.search(s)
if share_match:
    new_share = '''            // Keep a persistent local copy before opening the share sheet.
            File docs = getExternalFilesDir(Environment.DIRECTORY_DOCUMENTS);
            if (docs == null) docs = getFilesDir();
            File dir = new File(docs, "تقارير التوزيع");
            if (!dir.exists() && !dir.mkdirs()) throw new Exception("تعذر إنشاء مجلد حفظ التقارير");

            String safeStamp = new SimpleDateFormat("yyyy-MM-dd - HH-mm", Locale.US).format(new Date());
            File file = new File(dir, "تقرير توزيع الكروت لهذا اليوم - " + safeStamp + ".pdf");
            PdfDocument pdf = new PdfDocument();
            try {
                int pageWidth = 595;
                int pageHeight = Math.max(1, (int) Math.ceil(bitmap.getHeight() * (pageWidth / (double) bitmap.getWidth())));
                PdfDocument.PageInfo pageInfo = new PdfDocument.PageInfo.Builder(pageWidth, pageHeight, 1).create();
                PdfDocument.Page page = pdf.startPage(pageInfo);
                RectF dst = new RectF(0, 0, pageWidth, pageHeight);
                page.getCanvas().drawBitmap(bitmap, null, dst, null);
                pdf.finishPage(page);
                try (FileOutputStream out = new FileOutputStream(file)) {
                    pdf.writeTo(out);
                    out.flush();
                }
            } finally {
                pdf.close();
                bitmap.recycle();
            }

            Uri uri = FileProvider.getUriForFile(this, "__AUTHORITY__", file);'''.replace("__AUTHORITY__", share_match.group(1))
    s = share_pattern.sub(lambda _: new_share, s, count=1)
elif 'new File(docs, "تقارير التوزيع")' not in s:
    raise SystemExit("Cannot locate report file creation block; refusing to patch unknown source.")

s = s.replace('shareIntent.setType("image/png");', 'shareIntent.setType("application/pdf");')
s = s.replace('Intent.createChooser(shareIntent, "مشاركة الفاتورة كصورة")',
              'Intent.createChooser(shareIntent, "مشاركة تقرير التوزيع PDF")')
s = s.replace('showErrorDialog("خطأ", "تعذر تجهيز صورة الفاتورة: " + ex.getMessage());',
              'showErrorDialog("خطأ", "تعذر تجهيز تقرير PDF: " + ex.getMessage());')

main.write_text(s, encoding="utf-8")
paths.write_text('''<?xml version="1.0" encoding="utf-8"?>
<paths xmlns:android="http://schemas.android.com/apk/res/android">
    <cache-path name="worker_reports" path="reports/" />
    <external-files-path name="worker_documents" path="Documents/" />
    <files-path name="internal_reports" path="." />
</paths>
''', encoding="utf-8")
print("Applied V24 sale prices and persistent PDF report changes.")
