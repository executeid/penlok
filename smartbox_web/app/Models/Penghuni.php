<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use App\Models\User;

class Penghuni extends Model
{
    protected $table = 'penghuni';

    protected $fillable = [
        'user_id',
        'nama',
        'email',
        'no_telp',
        'no_kamar',
        'role',
        'status_wajah'
    ];

    // ✅ Relasi balik ke User
    public function user()
    {
        return $this->belongsTo(User::class);
    }
}
