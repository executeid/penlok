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

<div class="container py-3">

    <h2 class="mb-4 fw-bold d-flex align-items-center">
        <i class="me-2"></i> Dashboard Admin
    </h2>

    <div class="row g-4">
        {{-- Training Data Wajah --}}
        <div class="col-md-6">
            <div class="card shadow-lg border-0 rounded-4 h-100">
                <div class="card-body text-center d-flex flex-column justify-content-center">

                    <div class="text-success mb-3" style="font-size: 2rem;">
                        <i class="bi bi-cpu-fill"></i>
                    </div>

                    <h5 class="fw-bold text-dark">Generate Data Wajah</h5>
                    <p class="text-muted mb-4">
                        Generate ulang seluruh data wajah penghuni yang tersedia
                    </p>

                    <form action="{{ route('admin.trainingUlang') }}" method="POST">
                        @csrf
                        <button class="btn btn-success px-4 rounded-pill shadow-sm">
                            <i class="bi bi-arrow-repeat me-2"></i>
                            Generate Ulang
                        </button>
                    </form>

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

    <!-- Log Aktivitas -->
    <div class="card mt-5 shadow-lg border-0 rounded-4">
        <div class="card-body">
            <h5 class="fw-bold mb-3 text-dark d-flex align-items-center">
                <i class="bi bi-clock-history me-2 text-primary"></i> Log Aktivitas Terbaru
            </h5>

            <div class="table-responsive">
                <table class="table table-hover align-middle">
                    <thead class="table-primary text-dark">
                        <tr>
                            <th>No</th>
                            <th>Tanggal</th>
                            <th>Nama</th>
                            <th>Aktivitas</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        @forelse ($logs as $index => $log)
                            <tr>
                                <td>{{ $loop->iteration }}</td>
                                <td>{{ $log->created_at ? \Carbon\Carbon::parse($log->created_at)->format('d M Y H:i') : '-' }}</td>
                                <td>{{ $log->user->name ?? 'Tidak diketahui' }}</td>
                                <td>{{ $log->activity }}</td>
                                <td>
                                    @if($log->status == 'Berhasil')
                                        <span class="badge rounded-pill bg-success d-flex align-items-center gap-1 justify-content-center">
                                            <i class="bi bi-check-circle-fill"></i> Berhasil
                                        </span>
                                    @elseif($log->status == 'Gagal')
                                        <span class="badge rounded-pill bg-danger d-flex align-items-center gap-1 justify-content-center">
                                            <i class="bi bi-x-circle-fill"></i> Gagal
                                        </span>
                                    @else
                                        <span class="badge rounded-pill bg-secondary">{{ $log->status ?? 'Tidak Diketahui' }}</span>
                                    @endif
                                </td>
                            </tr>
                        @empty
                            <tr>
                                <td colspan="5" class="text-center text-muted py-4 fst-italic">
                                    <i class="bi bi-inbox me-2"></i> Belum ada aktivitas tercatat.
                                </td>
                            </tr>
                        @endforelse
                    </tbody>
                </table>
            </div>

            {{-- Tombol ke halaman history --}}
            <div class="d-flex justify-content-end mt-3">
                <a href="{{ route('admin.history.index') }}" class="btn btn-outline-primary rounded-pill shadow-sm">
                    <i class="bi bi-journal-text me-2"></i> Lihat Semua Riwayat
                </a>
            </div>
        </div>
    </div>
</div>

<style>
    /* Efek hover untuk tabel */
    .table-hover tbody tr:hover {
        background-color: #f1f9ff;
        transition: all 0.3s ease;
    }

    /* Animasi lembut */
    .card {
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    .card:hover {
        transform: translateY(-4px);
        box-shadow: 0px 4px 15px rgba(0,0,0,0.08);
    }

    /* Badge status */
    .badge {
        font-size: 0.9rem;
        padding: 0.45em 0.7em;
    }

    /* Efek loading text sensor */
    #status {
        animation: fadeBlink 1.8s infinite;
    }
    @keyframes fadeBlink {
        0%, 100% { opacity: 0.6; }
        50% { opacity: 1; }
    }
</style>

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
