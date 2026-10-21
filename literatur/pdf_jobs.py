"""Konversi PDF buku ke gambar halaman di background thread, dengan progress yang bisa di-poll.

Progress disimpan di file JSON (media/extract/progress/<book_id>.json) supaya bisa dibaca
dari worker web mana pun.
"""
import json
import logging
import os
import shutil
import threading
import time

from django.conf import settings
from django.db import connection
from pdf2image import convert_from_path, pdfinfo_from_path

logger = logging.getLogger(__name__)

CHUNK_PAGES = 5
STALE_SECONDS = 300


def _progress_path(book_id):
    return os.path.join(settings.MEDIA_ROOT, 'extract', 'progress', f'{book_id}.json')


def _write_progress(book_id, **data):
    path = _progress_path(book_id)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f'{path}.{threading.get_ident()}.tmp'
    with open(tmp, 'w') as f:
        json.dump(data, f)
    os.replace(tmp, path)


def read_progress(book_id):
    path = _progress_path(book_id)
    try:
        with open(path) as f:
            data = json.load(f)
        age = time.time() - os.path.getmtime(path)
    except (OSError, ValueError):
        return {'status': 'unknown', 'percent': 0, 'message': 'Tidak ada proses berjalan.'}
    if data.get('status') == 'processing' and age > STALE_SECONDS:
        return {'status': 'error', 'percent': data.get('percent', 0),
                'message': 'Proses terhenti (server restart?). Unggah ulang file PDF.'}
    return data


def _right_half(image):
    """Halaman 1 PDF berupa spread 2 halaman (landscape): ambil sisi kanan saja."""
    w, h = image.size
    if w <= h:
        return image
    return image.crop((w // 2, 0, w, h))


def _convert(book_id, pdf_path, activate):
    from .models import Books

    images_dir = os.path.join(settings.MEDIA_ROOT, 'extract', 'pdf_full', str(book_id))
    try:
        _write_progress(book_id, status='processing', percent=0, message='Membaca file PDF...')
        total = int(pdfinfo_from_path(pdf_path)['Pages'])

        shutil.rmtree(images_dir, ignore_errors=True)
        os.makedirs(images_dir)

        done = 0
        for first in range(1, total + 1, CHUNK_PAGES):
            last = min(first + CHUNK_PAGES - 1, total)
            for offset, image in enumerate(convert_from_path(pdf_path, first_page=first, last_page=last)):
                if first + offset == 1:
                    image = _right_half(image)
                image.save(os.path.join(images_dir, f'{first + offset}.jpg'), 'JPEG')
            done = last
            _write_progress(book_id, status='processing', percent=int(done * 100 / total),
                            message=f'Memproses halaman {done} dari {total}')

        updates = {'halaman': total}
        if activate:
            updates['is_active'] = True
        # queryset.update(): Books.save() punya cabang khusus dan tidak boleh dipanggil di sini
        Books.objects.filter(pk=book_id).update(**updates)
        os.remove(pdf_path)
        _write_progress(book_id, status='done', percent=100, message=f'Selesai, {total} halaman diproses.')
    except Exception as exc:
        logger.exception('Konversi PDF gagal untuk buku %s', book_id)
        shutil.rmtree(images_dir, ignore_errors=True)
        _write_progress(book_id, status='error', percent=0, message=f'Gagal memproses PDF: {exc}')
    finally:
        connection.close()


def start_pdf_conversion(book, activate=False):
    """Jalankan konversi PDF `book.pdf_full` di background. `activate`: aktifkan buku bila sukses."""
    pdf_path = os.path.join(settings.MEDIA_ROOT, book.pdf_full.name)
    _write_progress(book.pk, status='processing', percent=0, message='Menunggu antrian...')
    threading.Thread(target=_convert, args=(book.pk, pdf_path, activate), daemon=True).start()
