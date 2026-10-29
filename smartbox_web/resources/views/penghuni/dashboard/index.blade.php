@extends('layouts.admin')

@section('content')
@if(session('login_success'))
<div class="toast-container position-fixed top-0 end-0 p-3">
    <div class="toast show text-bg-success border-0">
        <div class="d-flex">
            <div class="toast-body">
                ✅ {{ session('login_success') }}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto"
                data-bs-dismiss="toast"></button>
        </div>
    </div>
</div>
@endif

@if(session('success'))
    <div class="alert alert-success alert-dismissible fade show" role="alert">
        {{ session('success') }}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    </div>
@endif

@if(session('error'))
    <div class="alert alert-danger alert-dismissible fade show" role="alert">
        {{ session('error') }}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    </div>
@endif

<div class="container">
    <h2 class="mb-4">Dashboard Penghuni</h2>
    
    <div class="row g-4 align-items-stretch">

    {{-- Status Data Wajah --}}
    <div class="col-md-6">
        <div class="card shadow-sm text-center h-100">
            <div class="card-body d-flex flex-column justify-content-center align-items-center">
 
                <div class="w-100" style="max-width: 360px;">

                    <h5 class="fw-bold mb-3">Status Data Wajah</h5>

                    @php
                        $folder = public_path('dataset/' . auth()->user()->name);
                        $jumlahFoto = 0;

                        if (is_dir($folder)) {
                            $files = array_diff(scandir($folder), ['.', '..']);
                            $jumlahFoto = count($files);
                        }
                    @endphp

                    @if($penghuni->status_wajah == 'belum')

                        <span class="badge bg-secondary px-4 py-2 mb-3">
                            ⚠️ Belum upload data wajah
                        </span>

                        <form action="{{ route('penghuni.uploadWajah') }}" method="POST" enctype="multipart/form-data">
                            @csrf

                            <input type="file"
                                   name="fotos[]"
                                   class="form-control mb-3"
                                   multiple
                                   required
                                   accept="image/*">

                            <small class="text-muted d-block mb-3">
                                Upload tepat 5 foto wajah
                            </small>

                            <button type="submit" class="btn btn-primary w-100">
                                Upload Wajah
                            </button>
                        </form>

                    @elseif($penghuni->status_wajah == 'captured')

                        <span class="badge bg-warning text-dark px-4 py-2 mb-3">
                            ⏳ Menunggu Generate
                        </span>

                        <p class="text-muted mb-0">
                            Data wajah berhasil diupload dan menunggu proses admin
                        </p>

                    @elseif ($penghuni->status_wajah == 'sudah')

                        <span class="badge bg-success px-4 py-2 mb-3">
                            ✅ Selesai Generate
                        </span>

                        <p class="text-muted mb-0">
                             Smart box siap dibuka dengan wajah Anda
                        </p>

                    @endif

                </div>

            </div>
        </div>
    </div>


    <!-- Sensor Ultrasonik -->
        <div class="col-md-6">
            <div class="card shadow-lg border-0 rounded-4 h-100 text-center">
                <div class="card-body d-flex flex-column justify-content-center">

                    <div class="mb-3 text-info" style="font-size: 2.5rem;">
                        <i class="bi bi-radar"></i>
                    </div>

                    <h5 class="fw-bold text-dark">
                        Monitoring Sensor Ultrasonik
                    </h5>

                    <h1 id="distance" class="fw-bold mt-3 text-dark">
                        -- cm
                    </h1>

                    <p id="status"
                        class="fw-semibold fs-5 text-secondary mt-2">
                        Memuat...
                    </p>

                </div>
            </div>
        </div>

    {{-- Log Aktivitas Penghuni --}}
    <div class="card mt-4 shadow-sm rounded-4">
        <div class="card-body">
            <h5 class="fw-bold mb-3">Log Aktivitas Terbaru</h5>
            <table class="table table-bordered table-striped">
                <thead class="table-dark">
                    <tr>
                        <th>No</th>
                        <th>Tanggal</th>
                        <th>Aktivitas</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    @forelse ($logs as $index => $log)
                        <tr>
                            <td>{{ $loop->iteration }}</td>
                            <td>{{ \Carbon\Carbon::parse($log->created_at)->format('d M Y H:i') }}</td>
                            <td>{{ $log->activity }}</td>
                            <td>
                                @if($log->status == 'Berhasil')
                                    <span class="badge bg-success">Berhasil</span>
                                @elseif($log->status == 'Gagal')
                                    <span class="badge bg-danger">Gagal</span>
                                @else
                                    <span class="badge bg-secondary">{{ $log->status ?? 'Tidak Diketahui' }}</span>
                                @endif
                            </td>
                        </tr>
                    @empty
                        <tr>
                            <td colspan="4" class="text-center text-muted">Belum ada aktivitas tercatat.</td>
                        </tr>
                    @endforelse
                </tbody>
            </table>

            <div class="d-flex justify-content-end">
                <a href="{{ route('penghuni.history.index') }}" class="btn btn-primary btn-sm mt-2">
                    Lihat Semua Riwayat
                </a>
            </div>
        </div>
    </div>
</div>

<script>
// Update data sensor tiap 3 detik
setInterval(() => {
    fetch("{{ route('admin.sensorData') }}")
        .then(res => res.json())
        .then(data => {
            document.getElementById('distance').innerText = data.distance + " cm";
            document.getElementById('status').innerText = data.status;
        });
}, 3000);
</script>
@endsection
