<?php

use App\Models\ActivityLog;
use Illuminate\Support\Facades\Auth;

if (!function_exists('activity')) {

    function activity($activity, $status = 'success')
    {
        ActivityLog::create([
            'user_id'  => Auth::id(),

            // ✅ AMAN: yang disimpan adalah NAMA STRING
            'nama'     => Auth::check() ? Auth::user()->name : 'System',

            'tanggal' => now(),
            'activity'=> $activity,

            // ✅ KUNCI: status hanya boleh success / failed
            'status'  => in_array($status, ['success', 'failed']) ? $status : 'success',
        ]);
    }
}

