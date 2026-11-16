<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
    public function up(): void
    {
        Schema::table('penghuni', function (Blueprint $table) {
            if (Schema::hasColumn('penghuni', 'kode_wajah')) {
                $table->dropColumn('kode_wajah'); // ✅ LANGSUNG DROP KOLOM SAJA
            }
        });
    }

    public function down(): void
    {
        Schema::table('penghuni', function (Blueprint $table) {
            $table->string('kode_wajah')->nullable();
        });
    }
};
