<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up()
    {
        Schema::table('penghuni', function (Blueprint $table) {
            $table->string('status_wajah')->default('belum')->after('no_kamar');
        });
    }

    public function down()
    {
        Schema::table('penghuni', function (Blueprint $table) {
            $table->dropColumn('status_wajah');
        });
    }
};
