@extends('layouts.admin')

@section('content')
<div class="container mt-4">
    <h3 class="mb-4 fw-bold">Riwayat Aktivitas Sistem</h3>

<form action="{{ route('penghuni.history.index') }}" method="GET" class="mb-3 d-flex gap-2">
    <input type="date" name="tanggal" class="form-control" value="{{ request('tanggal') }}">
    
    <input type="text" name="search" class="form-control" placeholder="Cari nama atau aktivitas..." value="{{ request('search') }}">
    
    <button type="submit" class="btn btn-primary">Filter</button>
    <a href="{{ route('penghuni.history.index') }}" class="btn btn-secondary">Reset</a>
</form>

    <div class="card shadow-sm rounded-4">
        <div class="card-body">
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
                            <td>{{ $log->created_at ? \Carbon\Carbon::parse($log->created_at)->format('d M Y H:i') : '-' }}</td>
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
                            <td colspan="5" class="text-center text-muted">Belum ada aktivitas tercatat.</td>
                        </tr>
                    @endforelse
                </tbody>
            </table>

            {{-- Pagination --}}
            <div class="d-flex justify-content-center">
                {{ $logs->links('pagination::bootstrap-5') }}
            </div>
        </div>
    </div>
</div>
@endsection
