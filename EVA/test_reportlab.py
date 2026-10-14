from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import LETTER
c = canvas.Canvas('reportlab_test.pdf', pagesize=LETTER)
c.drawString(100, 750, 'ReportLab test')
c.save()
print('wrote reportlab_test.pdf')
