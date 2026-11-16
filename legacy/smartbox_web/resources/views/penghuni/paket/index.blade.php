@extends('layouts.admin')

@section('content')
<div class="container">
    <h3 class="mb-4 fw-bold">
        <i class="bi bi-box-seam me-2"></i> Daftar Paket Saya
    </h3>

    <a href="{{ route('penghuni.paket.create') }}" class="btn btn-primary mb-4 shadow-sm">
        <i class="bi bi-plus-circle me-2"></i> Tambah Nomor Resi
    </a>

    @if(session('success'))
        <div class="alert alert-success alert-dismissible fade show shadow-sm" role="alert">
            <i class="bi bi-check-circle me-2"></i>{{ session('success') }}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    @endif

    @if(session('error'))
        <div class="alert alert-danger alert-dismissible fade show shadow-sm">
            <i class="bi bi-exclamation-circle me-2"></i>
            {{ session('error') }}

            <button type="button"
                class="btn-close"
                data-bs-dismiss="alert">
            </button>
        </div>
    @endif

    <div class="card shadow-sm border-0">
        <div class="card-body p-0">
            <table class="table table-hover mb-0 align-middle">
                <thead class="table-dark">
                    <tr>
                        <th class="text-center" style="width: 5%">No</th>
                        <th>Nomor Resi</th>
                        <th>Status</th>
                        <th>Tanggal Update</th>
                        <th class="text-center" style="width: 15%">Aksi</th>
                    </tr>
                </thead>
                <tbody>
                    @forelse($pakets as $index => $paket)
                        <tr>
                            <td class="text-center fw-semibold">{{ $index + 1 }}</td>
                            <td class="fw-medium">{{ $paket->nomor_resi }}</td>
                            <td>
                                {{-- Dalam perjalanan --}}
                                @if($paket->status == 'Dalam perjalanan')
                                    <span class="badge bg-warning text-dark px-3 py-2">
                                        <i class="bi bi-truck me-1"></i>
                                        Dalam Perjalanan
                                    </span>
                                {{-- Diterima --}}    
                                @elseif($paket->status == 'Diterima')
                                    <span class="badge bg-success px-3 py-2">
                                        <i class="bi bi-box-seam me-1"></i> Diterima
                                    </span>
                                {{-- Diambil --}}
                                @elseif($paket->status == 'Diambil')
                                    <span class="badge bg-primary px-3 py-2">
                                        <i class="bi bi-check-circle me-1"></i>
                                        Diambil
                                    </span>
                                {{-- Dibatalkan --}}
                                @elseif($paket->status == 'Dibatalkan')
                                    <span class="badge bg-danger px-3 py-2">
                                        <i class="bi bi-x-circle me-1"></i>
                                        Dibatalkan
                                    </span>    
                                @else
                                    <span class="badge bg-secondary px-3 py-2">
                                        {{ $paket->status }}
                                    </span>
                                @endif
                            </td>
                            <td>{{ $paket->updated_at->format('d M Y H:i') }}</td>
                            <td class="text-center">
                                {{-- hanya boleh batal saat masih perjalanan --}}
                                @if($paket->status == 'Dalam perjalanan')
                                    <form action="{{ route('penghuni.paket.destroy', $paket->id) }}"
                                          method="POST"
                                          class="d-inline"
                                        onsubmit="return confirm('Apakah Anda yakin ingin membatalkan paket ini?');">
                                        @csrf
                                        @method('PUT')
                                        <button type="submit"
                                                class="btn btn-outline-danger btn-sm rounded-circle shadow-sm"
                                                title="Batalkan Paket">
                                            <i class="bi bi-x-lg"></i>
                                        </button>
                                    </form>
                                @else
                                    <span class="text-muted small fst-italic">—</span>
                                @endif
                            </td>
                        </tr>
                    @empty
                        <tr>
                            <td colspan="5" class="text-center py-4 text-muted fst-italic">Belum ada paket terdaftar</td>
                        </tr>
                    @endforelse
                </tbody>
            </table>
        </div>
    </div>
</div>

<style>
    .table-hover tbody tr:hover {
        background-color: #f8f9fa !important;
        transition: background-color 0.3s ease;
    }
    .btn-outline-danger.btn-sm {
        transition: all 0.3s ease;
    }
    .btn-outline-danger.btn-sm:hover {
        background-color: #dc3545;
        color: white;
        transform: scale(1.1);
    }
</style>
@endsection
