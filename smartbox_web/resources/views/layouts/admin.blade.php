<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <title>
        @if(auth()->check() && auth()->user()->role === 'admin')
            Admin Panel
        @elseif(auth()->check() && auth()->user()->role === 'penghuni')
            Dashboard Penghuni
        @else
            SmartBox System
        @endif
    </title>

    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.css" rel="stylesheet">

    <style>
        body {
            display: flex;
            min-height: 100vh;
            flex-direction: row;
            background-color: #f8f9fa;
        }
        .sidebar {
            width: 250px;
            background-color: #343a40;
            color: white;
            padding-top: 20px;
        }
        .sidebar a {
            color: white;
            text-decoration: none;
            display: block;
            padding: 10px 20px;
            border-radius: 8px;
        }
        .sidebar a:hover,
        .sidebar a.active {
            background-color: #495057;
        }
        .content {
            flex: 1;
            display: flex;
            flex-direction: column;
            padding: 30px;
        }
        .main-content {
            flex: 1;
        }
        footer {
            text-align: center;
            font-size: 0.85rem;
            color: #6c757d;
            margin-top: 20px;
            padding-top: 10px;
            border-top: 1px solid #dee2e6;
        }
    </style>
</head>
<body>

    <!-- Sidebar -->
    <div class="sidebar">

        {{-- ====== SIDEBAR ADMIN ====== --}}
        @if(auth()->check() && auth()->user()->role === 'admin')
            <h4 class="text-center mb-4">Admin Panel</h4>

            <a href="{{ route('admin.dashboard.index') }}" class="{{ request()->is('admin/dashboard*') ? 'active' : '' }}">
                <i class="bi bi-house-door me-2"></i> Dashboard
            </a>

            <a href="{{ route('admin.datapenghuni.index') }}" class="{{ request()->is('admin/datapenghuni*') ? 'active' : '' }}">
                <i class="bi bi-people-fill me-2"></i> Data Penghuni
            </a>

            <a href="{{ route('admin.history.index') }}" class="{{ request()->is('admin/history*') ? 'active' : '' }}">
                <i class="bi bi-clock-history me-2"></i> History
            </a>

        {{-- ====== SIDEBAR PENGHUNI ====== --}}
        @elseif(auth()->check() && auth()->user()->role === 'penghuni')
            <h4 class="text-center mb-4">Penghuni</h4>

            <a href="{{ route('penghuni.dashboard.index') }}" class="{{ request()->is('penghuni/dashboard*') ? 'active' : '' }}">
                <i class="bi bi-house-door me-2"></i> Dashboard
            </a>

            <a href="{{ route('penghuni.paket.index') }}" class="{{ request()->is('penghuni/paket*') ? 'active' : '' }}">
                <i class="bi bi-plus-circle me-2"></i> Input Resi
            </a>

            <a href="{{ route('penghuni.history.index') }}" class="{{ request()->is('penghuni/history*') ? 'active' : '' }}">
                <i class="bi bi-clock-history me-2"></i> History
            </a>
        @endif

        <a href="{{ route('logout') }}" class="text-danger mt-3">
            <i class="bi bi-box-arrow-right me-2"></i> Logout
        </a>

    </div>

    <!-- Konten -->
    <div class="content">
        <div class="main-content">
            @yield('content')
        </div>
        <footer>
            © {{ date('Y') }} SmartBox Management System | All rights reserved.
        </footer>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/sweetalert2@11"></script>
    <script>
        @if(session('success'))
            Swal.fire({
                icon: 'success',
                title: 'Berhasil',
                text: "{{ session('success') }}",
                timer: 5000,
                showConfirmButton: false
            });
        @endif

        @if(session('error'))
            Swal.fire({
                icon: 'error',
                title: 'Gagal',
                text: "{{ session('error') }}",
                timer: 2500,
                showConfirmButton: true
            });
        @endif
    </script>
</body>
</html>
