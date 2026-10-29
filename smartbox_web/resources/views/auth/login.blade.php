<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <title>Login Smart Box</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css">

    <style>
        body {
            min-height: 100vh;
            background: url("/images/bg-login.jpg") no-repeat center center;
            background-size: cover;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        /* Overlay gelap 
        body::before {
            content: "";
            position: absolute;
            inset: 0;
            background: rgba(0, 0, 0, 0.6);
            z-index: 0;
        } */

        .container {
            position: relative;
            z-index: 1;
        }

        .login-card {
            border-radius: 18px;
            overflow: hidden;
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(6px);
            animation: fadeIn 0.6s ease;
        }

        .login-header {
            background: linear-gradient(135deg, #dc9fd4, #bb76d1);
            padding: 25px;
            text-align: center;
            color: white;
        }

        .form-control {
            border-radius: 10px;
            padding: 10px;
        }

        .btn-login {
            background: linear-gradient(135deg, #dc9fd4, #bb76d1);
            border: none;
            border-radius: 10px;
            font-weight: 600;
        }

        .btn-login:hover {
            opacity: 0.9;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
    </style>
</head>
<body>

<div class="container">
    <div class="row justify-content-center">
        <div class="col-md-4">
            <div class="card shadow login-card">
                <div class="login-header">
                    <h4>🔐 Smart Box Login</h4>
                    <small>Sistem Keamanan Paket Otomatis</small>
                </div>
                <div class="card-body p-4">

                    {{-- ALERT LOGOUT BERHASIL --}}
                    @if(session('logout_success'))
                        <div class="alert alert-success">
                            {{ session('logout_success') }}
                        </div>
                    @endif

                    {{-- ALERT LOGIN GAGAL --}}
                    @if(session('error'))
                        <div class="alert alert-danger">
                            {{ session('error') }}
                        </div>
                    @endif

                    <form action="{{ route('login.post') }}" method="POST">
                        @csrf

                        <div class="mb-3">
                            <label>Email</label>
                            <input type="email" name="email" class="form-control" required autofocus>
                        </div>

                        <div class="mb-3">
                            <label>Password</label>
                            <input type="password" name="password" class="form-control" required>
                        </div>

                        <button type="submit" class="btn btn-login w-100 text-white mt-2">
                            Masuk
                        </button>
                    </form>

                </div>
            </div>
        </div>
    </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
