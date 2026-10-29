<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SmartBox Web</title>

    {{-- Bootstrap CSS --}}
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">

    <style>
        body {
            background-color: #f9fafc;
            margin: 0;
            padding: 0;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }

        .sidebar {
            height: 100vh;
            background-color: #ffffff;
            box-shadow: 2px 0 8px rgba(0, 0, 0, 0.1);
            min-width: 220px;
        }

        .sidebar a {
            text-decoration: none;
            color: #333;
            display: block;
            padding: 12px 20px;
            transition: background 0.2s;
        }

        .sidebar a:hover {
            background-color: #f0f4ff;
        }

        .sidebar a.active {
            background-color: #e8f0fe;
            font-weight: 600;
            border-left: 4px solid #007bff;
            color: #007bff;
        }

        .content {
            padding: 30px;
            flex-grow: 1;
            background-color: #f9fafc;
        }
    </style>
</head>
<body>
    <div class="d-flex">
        <div class="sidebar">
            <h4 class="p-3 text-primary">SmartBox</h4>

            <a href="{{ route('dashboard.admin') }}" 
               class="{{ request()->is('dashboard') ? 'active' : '' }}">
               Dashboard
            </a>

            <a href="{{ route('dashboard.penghuni') }}" 
               class="{{ request()->is('penghuni*') ? 'active' : '' }}">
               Data Penghuni
            </a>

            <a href="{{ route('logout') }}">Logout</a>
        </div>

        <div class="content">
            @yield('content')
        </div>
    </div>

    {{-- Bootstrap JS --}}
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
