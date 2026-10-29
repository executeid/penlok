@extends('layouts.admin')

@section('content')
<style>
    .table th, .table td {
        padding: 8px 12px !important;
        font-size: 14px;
        vertical-align: middle !important;
    }
    .table thead th {
        font-size: 14px;
        font-weight: 600;
    }
    .badge-status {
        padding: 5px 10px;
        font-size: 12px;
        border-radius: 6px;
    }
    .btn-sm-custom {
        padding: 4px 10px !important;
        font-size: 12px !important;
        border-radius: 6px;
    }
    .aksi-btn {
        width: 80px;
    }
</style>

<div class="container py-4">

    <div class="card shadow-sm border-0">
        <div class="card-body">

            <!-- Header -->
            <div class="d-flex justify-content-between align-items-center mb-4">
                <h3 class="fw-bold mb-0">Data Penghuni</h3>

                <button class="btn btn-primary px-3 shadow-sm" data-bs-toggle="modal" data-bs-target="#tambahModal">
                    <i class="bi bi-person-plus me-1"></i> Tambah Penghuni
                </button>
            </div>

            <!-- Search -->
            <form method="GET" action="{{ route('admin.datapenghuni.index') }}" class="d-flex mb-3">
                <input type="text" name="search" class="form-control me-2"
                    placeholder="Cari nama atau email..." value="{{ $search ?? '' }}">
                <button type="submit" class="btn btn-secondary">
                    <i class="bi bi-search"></i>
                </button>
            </form>

            <!-- Table -->
            <div class="table-responsive">
                <table class="table table-striped table-hover text-center align-middle">
                    <thead class="table-dark">
                        <tr>
                            <th style="width: 5%">ID</th>
                            <th style="width: 15%">Nama</th>
                            <th style="width: 20%">Email</th>
                            <th style="width: 12%">No Telpon</th>
                            <th style="width: 10%">No Kamar</th>
                            <th style="width: 10%">Status</th>
                            <th style="width: 28%">Aksi</th>
                        </tr>
                    </thead>
                    <tbody>
                        @forelse ($penghuni as $item)
                            <tr>
                                <td>{{ $item->id }}</td>
                                <td>{{ $item->nama }}</td>
                                <td>{{ $item->email }}</td>
                                <td>{{ $item->no_telp }}</td>
                                <td>{{ $item->no_kamar }}</td>

                                <!-- STATUS WAJAH -->
                                <td>
                                    @php
                                        $folder = public_path('dataset/' . $item->nama);
                                        $jumlahFoto = 0;

                                        if (is_dir($folder)) {
                                            $files = array_diff(scandir($folder), ['.', '..']);
                                            $jumlahFoto = count($files);
                                        }
                                    @endphp
                                    @if($item->status_wajah == 'sudah')
                                        <span class="badge bg-success badge-status">Selesai</span>
                                    @elseif($item->status_wajah == 'captured')
                                        <span class="badge bg-warning text-dark badge-status">Menunggu<br>Training</span>
                                    @else
                                        <span class="badge bg-secondary badge-status">Belum</span>
                                    @endif
                                </td>

                                <!-- AKSI -->
                                <td class="d-flex justify-content-center gap-2">

                                    <!-- Tombol Training -->
                                    @if ($item->status_wajah == 'captured')
                                        <form action="{{ route('admin.datapenghuni.training', $item->id) }}" method="POST">
                                            @csrf
                                            <button type="submit"
                                                onclick="return confirm('Proses training wajah untuk {{ $item->nama }}?')"
                                                class="btn btn-warning btn-sm-custom aksi-btn">
                                                <i class="bi bi-cpu"></i> Proses
                                            </button>
                                        </form>
                                    @endif

                                    <!-- Tombol Hapus -->
                                    <form action="{{ route('admin.datapenghuni.hapus', $item->id) }}"
                                          method="POST"
                                          onsubmit="return confirm('Yakin hapus data ini?')">
                                        @csrf
                                        @method('DELETE')
                                        <button class="btn btn-danger btn-sm-custom aksi-btn">
                                            <i class="bi bi-trash-fill"></i> Hapus
                                        </button>
                                    </form>
                                </td>

                            </tr>
                        @empty
                            <tr>
                                <td colspan="7" class="text-muted py-3">Tidak ada data penghuni</td>
                            </tr>
                        @endforelse
                    </tbody>
                </table>
            </div>

        </div>
    </div>
</div>

<!-- Modal Tambah Penghuni -->
<div class="modal fade" id="tambahModal" tabindex="-1">
    <div class="modal-dialog modal-dialog-centered">
        <form action="{{ route('admin.datapenghuni.store') }}" method="POST" class="modal-content shadow">
            @csrf
            <div class="modal-header bg-primary text-white">
                <h5 class="modal-title"><i class="bi bi-person-plus me-2"></i> Tambah Penghuni</h5>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
            </div>

            <div class="modal-body">

                <div class="mb-3">
                    <label class="fw-semibold">Nama</label>
                    <input type="text" name="nama" class="form-control" required>
                </div>

                <div class="mb-3">
                    <label class="fw-semibold">Email</label>
                    <input type="email" name="email" class="form-control" required>
                </div>

                <div class="mb-3">
                    <label class="fw-semibold">Password</label>
                    <input type="password" name="password" class="form-control" required>
                </div>

                <div class="mb-3">
                    <label class="fw-semibold">Nomor Telpon</label>
                    <input type="text" name="no_telp" class="form-control" required>
                </div>

                <div class="mb-3">
                    <label class="fw-semibold">Nomor Kamar</label>
                    <input type="number" name="no_kamar" class="form-control" required>
                </div>

                <div class="mb-3">
                    <label class="fw-semibold">ID Telegram</label>
                    <input type="text" name="telegram_id" class="form-control" required>
                    <small class="text-muted">Masukkan Chat ID Telegram pengguna</small>
                </div>

            </div>

            <div class="modal-footer">
                <button class="btn btn-secondary" data-bs-dismiss="modal">Batal</button>
                <button class="btn btn-primary">Simpan</button>
            </div>
        </form>
    </div>
</div>

@endsection
