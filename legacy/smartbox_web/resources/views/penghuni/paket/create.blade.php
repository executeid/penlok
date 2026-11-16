@extends('layouts.admin')

@section('content')
<div class="container d-flex justify-content-center">
    <div class="col-md-6">

        <div class="card shadow-sm">
            <div class="card-body">

                <h4 class="mb-4 text-center">
                    <i class="bi bi-box-seam me-2"></i> Tambah Nomor Resi
                </h4>

                <form action="{{ route('penghuni.paket.store') }}" method="POST">
                    @csrf

                    <div class="mb-3">
                        <label for="nomor_resi" class="form-label fw-semibold">
                            Nomor Resi Pengiriman
                        </label>

                        <div class="input-group">
                            <span class="input-group-text">
                                <i class="bi bi-upc-scan"></i>
                            </span>
                            <input 
                                type="text" 
                                class="form-control @error('nomor_resi') is-invalid @enderror" 
                                id="nomor_resi" 
                                name="nomor_resi" 
                                placeholder="Contoh: JNE1234567890"
                                required
                            >
                        </div>

                        <small class="text-muted">
                            Masukkan nomor resi paket yang akan diterima oleh smart box.
                        </small>

                        @error('nomor_resi')
                            <div class="text-danger small mt-1">
                                {{ $message }}
                            </div>
                        @enderror
                    </div>

                    <div class="d-flex justify-content-end gap-2 mt-4">
                        <a href="{{ route('penghuni.paket.index') }}" class="btn btn-outline-secondary">
                            Kembali
                        </a>
                        <button type="submit" class="btn btn-success">
                            Simpan
                        </button>
                    </div>

                </form>

            </div>
        </div>

    </div>
</div>
@endsection
