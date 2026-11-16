<?php

namespace App\Http\Controllers\admin;

use App\Http\Controllers\Controller;
use Illuminate\Http\Request;

class MonitoringController extends Controller
{
    public function index()
    {
        return view('admin.monitoring');
    }

    public function progress()
    {
        $file = storage_path('app/training_progress.json');

        if (!file_exists($file)) {
            return ['progress' => 0, 'status' => 'Menunggu proses training dimulai...'];
        }

        $data = json_decode(file_get_contents($file), true);

        return [
            'progress' => $data['progress'] ?? 0,
            'status' => $data['status'] ?? 'Sedang memulai...'
        ];
    }
}
