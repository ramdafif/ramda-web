# Panduan Admin RAMDA

## Masuk dan keamanan

Buka `/admin`, masukkan email dan kata sandi yang dibuat lewat perintah `create-admin`. Jika 2FA aktif, masukkan kode autentikator. Terlalu banyak percobaan gagal akan mengunci sementara. Gunakan halaman Keamanan untuk mengganti kata sandi dan menyiapkan 2FA. Simpan kunci autentikator di tempat aman. Menu Integrasi & Akun hanya menampilkan apakah kunci server tersedia; nilainya tidak ditampilkan.

## Draf, pratinjau, dan Publish

1. Pilih bagian yang ingin diedit di navigasi.
2. Edit isian Indonesia. English boleh kosong karena pengalih bahasa belum diaktifkan.
3. Gunakan tombol tambah/hapus item untuk daftar. Field gambar menerima referensi yang disalin dari Media.
4. Centang **Siap diterbitkan saat Publish** untuk menayangkan. Jangan centang pada artikel yang masih draf; artikel juga perlu status `published`.
5. Centang **Saya sudah memverifikasi konten ini** hanya setelah isi, angka, status dan izin pemakaiannya benar.
6. Klik **Simpan draf**. Situs publik belum berubah.
7. Gunakan **Pratinjau draf** untuk tautan pribadi yang berlaku sepuluh menit. Pratinjau diberi noindex dan tidak di-cache. Jangan membagikan tautan kepada pihak yang tidak boleh membaca draf.
8. Klik **Publish** di header. Semua perubahan siap terbit, penarikan konten dan urutan diperbarui bersama. Perubahan biasanya muncul dalam beberapa detik. Notifikasi fallback cache tidak berarti Publish gagal.

Banner di atas dashboard menunjukkan jumlah konten placeholder. Statistik dan testimoni placeholder disembunyikan. Testimoni juga memerlukan `consent_given=true`. Jangan mengisi angka, logo klien atau testimoni rekaan untuk menghilangkan banner.

## Beranda dan menu

**Section Beranda:** ubah judul, eyebrow, subtitle, tombol dan visibilitas. Tarik pegangan untuk mengurutkan atau pakai tombol ↑ ↓. Kosongkan pencarian/filter sebelum mengurutkan. Navbar dan footer selalu menjadi bingkai halaman; bagian konten mengikuti urutan section. Section dengan daftar konten kosong otomatis hilang.

**Hero:** ubah headline dan kata yang disorot; kata yang disorot harus sama persis dengan bagian headline. Gambar, tagline tulisan tangan dan video perkenalan bersifat opsional.

**Pengaturan Situs:** nama brand, logo, tagline, menu, CTA, WhatsApp, footer, SEO umum dan analytics. Isi WhatsApp dengan format internasional angka saja, misalnya diawali 628. Nomor kosong menyembunyikan tombol WhatsApp. Social link kosong tidak ditampilkan. Ketersediaan proyek memiliki sakelar dan teks sendiri.

**Statistik:** isi hanya angka yang dapat dibuktikan. Ubah visible menjadi aktif, verifikasi, siapkan terbit, simpan dan Publish. Pastikan tidak bertentangan dengan metrik proyek.

## Proyek dan artikel

Proyek memiliki ringkasan, status, stack, gambar, galeri, tautan demo/repo dan studi kasus **problem → solution → result**. Status hanya berasal dari pilihan yang disediakan. Jangan memberi status Live jika produk belum benar-benar live. Slug harus huruf kecil, angka atau tanda hubung; slug yang sudah dipublikasikan dikunci untuk melindungi tautan.

Gunakan editor Markdown untuk isi panjang. Pratinjau dirender dan dibersihkan di server; HTML berbahaya tidak dijalankan. Artikel draf tidak masuk beranda, daftar publik, RSS atau sitemap. Saat pertama kali status artikel menjadi published tanpa waktu, waktu terbit otomatis diisi. Jika mengisi sendiri, gunakan format ISO lengkap dengan zona waktu, misalnya `2026-10-30T09:00:00+07:00`. Waktu mendatang menjadwalkan publikasi; centang siap terbit lalu Publish tetap diperlukan.

Harga, FAQ dan testimoni tidak memiliki contoh palsu. Tambahkan konten sungguhan untuk memunculkan section. Testimoni membutuhkan persetujuan pemilik kutipan. Tombol penarikan mengubah kesiapan terbit menjadi draf; Publish untuk menarik dari publik. Setelah ditarik dari publik, tombol berubah menjadi Hapus draf untuk menghapus entri. Audit tindakannya tetap disimpan.

## Media

Unggah JPG, PNG, WebP, AVIF atau SVG, maksimal 8 MB. Gambar raster dibatasi 24 megapiksel agar aman untuk VPS kecil. Beri deskripsi alt yang menjelaskan gambar, bukan nama file. Server membuat AVIF/WebP dengan beberapa ukuran dan menghapus EXIF. SVG dibersihkan dari skrip dan sumber eksternal.

Buka **Referensi untuk konten**, klik **Salin referensi**, lalu pada field gambar gunakan **Tempel referensi dari Media → Gunakan media**. Referensi menyertakan alt, ukuran dan srcset. Saat mengubah alt di Media, periksa juga alt pada referensi konten yang sudah dipakai; referensi adalah snapshot saat dipilih. Media yang masih digunakan oleh draf atau publik tidak bisa dihapus.

## AI dan lead

AI awalnya dinonaktifkan. Administrator teknis mengisi kunci, model, harga token, allowlist, anggaran dan Turnstile di server. Anda mengelola pesan sambutan, prompt panduan, saran pertanyaan dan dokumen pengetahuan di CMS. Gunakan hanya satu model yang sesuai dengan environment. Publikasikan dokumen yang boleh dibaca semua pengunjung. Jangan masukkan kunci, dokumen rahasia atau data pelanggan.

**Kill switch** mematikan API segera setelah disimpan. Publish juga untuk menghilangkan section. Dashboard AI menampilkan tujuh hari terakhir dan estimasi biaya konservatif. Batas demo menampilkan pesan ramah, bukan mencoba model berbayar lain.

Lead baru masuk ke **Inbox Leads**. Cari atau filter status, baca pesan, tambah catatan internal dan ubah menjadi contacted/won/lost. CSV tersedia untuk pekerjaan internal. Jika notifikasi gagal, lead tetap tersimpan dan status pengiriman bisa diperiksa. Perubahan notifikasi/SMTP/Telegram harus dilakukan oleh pengelola server dan diuji ke tujuan yang benar.

## Backup

Unduh **konten JSON** dan **uploads ZIP** dari Backup. Simpan keduanya secara aman. JSON dapat diimpor sebagai draf kerja; tidak langsung mengganti situs publik. Pulihkan uploads ZIP hasil ekspor CMS melalui formulir terpisah, tinjau konten dan Publish. Maksimum ZIP 64 MB, isi 128 MB; backup besar dipulihkan melalui prosedur VPS. Backup konten tidak menyertakan kata sandi, kunci API atau data lead. Backup server lengkap dan latihan pemulihan diatur oleh pengelola VPS.

Audit Log mencatat siapa melakukan tindakan dan targetnya tanpa menyimpan kunci atau salinan percakapan. Log tidak dapat diubah dari CMS.
