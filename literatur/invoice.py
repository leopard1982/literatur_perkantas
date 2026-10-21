import io
import re

from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .models import MyPayment, MyPaymentDetail

# nomor invoice dibuat di paymentProcess: 'ltn' + tahun + uuid4
INVOICE_ID_RE = re.compile(r'ltn\d{4}[0-9a-fA-F-]{36}')

BULAN = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 'Juli',
         'Agustus', 'September', 'Oktober', 'November', 'Desember']


def invoice_id_from_text(text):
    match = INVOICE_ID_RE.search(text or '')
    return match.group(0) if match else None


def get_downloadable_payment(user, payment_id):
    """Invoice hanya untuk pembayaran milik user yang sudah disetujui."""
    if user is None or not payment_id:
        return None
    return MyPayment.objects.filter(payment=payment_id, user=user, is_verified=True).first()


def _rupiah(value):
    return 'Rp {:,.0f}'.format(value).replace(',', '.')


def _tanggal(value):
    return f'{value.day} {BULAN[value.month - 1]} {value.year}'


def build_invoice_pdf(payment):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm, bottomMargin=2 * cm,
    )
    styles = getSampleStyleSheet()
    width = A4[0] - 4 * cm

    user = payment.user
    detail = getattr(user, 'userdetail', None)
    nama = (getattr(detail, 'nama_lengkap', '') or user.username) if user else '-'
    items = list(MyPaymentDetail.objects.filter(payment=payment).select_related('book').order_by('id'))

    elements = [
        Paragraph('INVOICE', styles['Title']),
        Paragraph('Literatur Perkantas Nasional', styles['Normal']),
        Spacer(1, 0.6 * cm),
    ]

    info = Table([
        ['No. Invoice', payment.payment],
        ['Tanggal', _tanggal(payment.created_at)],
        ['Nama Pembeli', nama],
        ['Email', user.email if user and user.email else '-'],
        ['Status', 'LUNAS'],
    ], colWidths=[width * 0.25, width * 0.75])
    info.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements += [info, Spacer(1, 0.8 * cm)]

    rows = [['No', 'Judul Buku', 'Harga']]
    for no, item in enumerate(items, start=1):
        judul = item.book.judul if item.book else '(buku dihapus)'
        rows.append([str(no), Paragraph(judul, styles['Normal']), _rupiah(item.harga)])
    rows.append(['', 'Total', _rupiah(payment.total)])

    table = Table(rows, colWidths=[width * 0.08, width * 0.62, width * 0.30], repeatRows=1)
    table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#273744')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (1, -1), (-1, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements += [table, Spacer(1, 1.2 * cm),
                 Paragraph('Terima kasih atas pembelian kaka. Tuhan memberkati!', styles['Normal'])]

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


def invoice_response(payment):
    response = HttpResponse(build_invoice_pdf(payment), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice-{payment.payment}.pdf"'
    return response
