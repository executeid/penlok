<?php

namespace App\Http\Controllers\admin;

use App\Http\Controllers\Controller;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use App\Models\Activitylog;

class DashboardController extends Controller
{
    public function index()
    {
        // Contoh: ambil data dari tabel log_aktivitas (ganti sesuai nama tabel kamu)
        $logs = DB::table('activity_logs')
                    ->orderBy('created_at', 'desc')
                    ->limit(10)
                    ->get();

        return view('admin.dashboard.index', compact('logs'));
    }
}
