<?php

use Illuminate\Support\Facades\Route;
use App\Http\Controllers\AuthController;
use App\Http\Controllers\admin\AdminController;
use App\Http\Controllers\penghuni\PenghuniController;
use App\Http\Controllers\admin\MonitoringController;

// ========================
// AUTH
// ========================
Route::get('/', [AuthController::class, 'showLogin'])->name('login');
Route::post('/login', [AuthController::class, 'login'])->name('login.post');
Route::get('/logout', [AuthController::class, 'logout'])->name('logout');

// ========================
// ADMIN
// ========================
Route::prefix('admin')->middleware('auth')->group(function () {
    Route::get('/dashboard/index', [AdminController::class, 'index'])->name('admin.dashboard.index');
    Route::post('/admin/training-ulang', [AdminController::class, 'trainingUlang'])->name('admin.trainingUlang');
    Route::get('/admin/sensor-data', [AdminController::class, 'getSensorData'])->name('admin.sensorData');
    Route::get('/datapenghuni/index', [AdminController::class, 'penghuni'])->name('admin.datapenghuni.index');
    Route::post('/datapenghuni', [AdminController::class, 'storePenghuni'])->name('admin.datapenghuni.store');
    Route::delete('/datapenghuni/{id}', [AdminController::class, 'hapusPenghuni'])->name('admin.datapenghuni.hapus');
    Route::post('/datapenghuni/training/{id}', [AdminController::class, 'training'])->name('admin.datapenghuni.training');
    Route::get('/history/index', [AdminController::class, 'history'])->name('admin.history.index');
    Route::get('/monitoring-training', [MonitoringController::class, 'index'])->name('admin.monitoring');
    Route::get('/progress-training', [MonitoringController::class, 'progress']);
});


// ========================
// PENGHUNI
// ========================
Route::prefix('penghuni')->middleware(['auth'])->group(function () {
    Route::get('/dashboard/index', [PenghuniController::class, 'dashboard'])->name('penghuni.dashboard.index');
    Route::post('/penghuni/upload-wajah', [PenghuniController::class, 'uploadWajah'])->name('penghuni.uploadWajah');
    Route::get('/paket', [PenghuniController::class, 'paketIndex'])->name('penghuni.paket.index');
    Route::get('/paket/create', [PenghuniController::class, 'paketCreate'])->name('penghuni.paket.create');
    Route::post('/paket/store', [PenghuniController::class, 'paketStore'])->name('penghuni.paket.store');
    Route::put('/paket/{id}', [PenghuniController::class, 'paketDestroy'])->name('penghuni.paket.destroy');
    Route::get('/history/index', [PenghuniController::class, 'history'])->name('penghuni.history.index');
});



