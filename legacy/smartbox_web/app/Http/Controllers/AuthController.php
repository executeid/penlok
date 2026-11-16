<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;

class AuthController extends Controller
{
    public function showLogin()
    {
        return view('auth.login');
    }

    public function login(Request $request)
    {
        $credentials = $request->only('email', 'password');

        if (Auth::attempt($credentials)) {
            $request->session()->regenerate();

            $user = Auth::user();

            // cek role
            if ($user->role === 'admin') {
                return redirect()
                    ->route('admin.dashboard.index')
                    ->with('login_success', 'Login berhasil. Selamat datang Admin.');
            }

            if ($user->role === 'penghuni') {
                return redirect()
                    ->route('penghuni.dashboard.index')
                    ->with('login_success', 'Login berhasil. Selamat datang Penghuni.');
            }

            return redirect()->route('dashboard')
                ->with('success', 'Login berhasil, selamat datang!');
        }

        return back()->with('error', 'Email atau password salah');
    }
    public function logout(Request $request)
    {
        Auth::logout(); // logout user

        // invalidate + regenerate session
        $request->session()->invalidate();
        $request->session()->regenerateToken();

        return redirect()->route('login')->with('logout_success', 'Anda berhasil logout.');
    }
}
