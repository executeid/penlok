<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;

class Paket extends Model
{
    use HasFactory;

    protected $fillable = [
        'user_id',
        'nomor_resi',
        'status',
        'jarak_sensor'
    ];

    public function user()
    {
        return $this->belongsTo(User::class);
    }
}

