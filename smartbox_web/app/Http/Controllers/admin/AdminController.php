<?php

namespace App\Http\Controllers\admin;

use App\Models\User;
use Illuminate\Support\Facades\Hash;
use App\Http\Controllers\Controller;
use App\Models\Activitylog;
use App\Models\Penghuni;
use App\Models\Paket;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\File;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Spatie\Activitylog\Models\Activity;


class AdminController extends Controller
{
    public function index()
    {
        $user = Auth::user();
        $logs = ActivityLog::latest()->take(5)->get(); // hanya 5 data terbaru
        $cameraMode = session('camera_mode', 'monitoring');
        return view('admin.dashboard.index', compact('logs', 'cameraMode'));
    }

    public function trainingUlang()
    {
        try {

            // ubah semua jadi proses dulu
            Penghuni::whereNotNull('id')
                ->update(['status_wajah' => 'captured']);

            $python = '"C:\\laragon\\bin\\python\\python-3.10\\python.exe"';
            $script = '"C:\\laragon\\www\\smartbox_web\\generate_embeddings.py"';

            $command = $python . ' ' . $script;

             exec($command, $output, $resultCode);

            if ($resultCode !== 0) {
                return back()->with('error', 'Training ulang gagal.');
            }

            // sukses semua jadi selesai
            Penghuni::where('status_wajah', 'captured')
                ->update(['status_wajah' => 'sudah']);

            Activitylog::create([
                'user_id' => auth::id(),
                'activity' => 'Training ulang seluruh penghuni berhasil',
                'status' => 'success',
                'tanggal' => now(),
            ]);

            return back()->with('success', 'Training ulang seluruh data berhasil.');

        } catch (\Exception $e) {

            return back()->with('error', $e->getMessage());
        }
    }

    public function getSensorData()
    {
        $paket = Paket::whereNotNull('jarak_sensor')
            ->latest('updated_at')
            ->first();

        if ($paket) {

            $distance = $paket->jarak_sensor;

            if ($distance >= 27 && $distance <= 29) {
                $status = 'Kosong';
            } else {
                $status = 'Paket Terdeteksi';
            }

            return response()->json([
                'distance' => $distance,
                'status' => $status
            ]);
        }

        return response()->json([
            'distance' => '--',
            'status' => 'Belum Ada Paket'
        ]);
    }

    public function penghuni(Request $request)
    {
        $search = $request->input('search'); // untuk pencarian

        $query = Penghuni::query();

        if (!empty($search)) {
            $query->where('nama', 'like', "%{$search}%")
                  ->orWhere('email', 'like', "%{$search}%");
    }

        $penghuni = $query->orderBy('id', 'asc')->paginate(10);

        // kirim variabel $search agar tidak error di blade
        return view('admin.datapenghuni.index', compact('penghuni', 'search'));
    }

    public function storePenghuni(Request $request)
    {
        $request->validate([
            'nama' => 'required|string|max:255',
            'email' => 'required|email|unique:users,email',
            'no_telp' => 'required|string|max:20',
            'password' => 'required|string|min:6',
            'no_kamar' => 'required|integer',
            'telegram_id' => 'required|string|max:30',
        ]);

        DB::beginTransaction();

        try {

            $user = User::create([
                'name' => $request->nama,
                'email' => $request->email,
                'password' => Hash::make($request->password),
                'role' => 'penghuni',
                'telegram_id' => $request->telegram_id,
            ]);

            $penghuni = Penghuni::create([
                'user_id' => $user->id,
                'nama' => $request->nama,
                'email' => $request->email,
                'no_telp' => $request->no_telp,
                'no_kamar' => $request->no_kamar,
                'status_wajah' => 'belum',
            ]);

            activity("Admin menambahkan penghuni: {$penghuni->nama}");

            DB::commit();

            // kirim telegram (opsional)
            try {

                $token = env('TELEGRAM_BOT_TOKEN');
                $chatId = $request->telegram_id;

                $message = "Akun Anda telah berhasil dibuat.\n";
                $message .= "Email: ".$request->email."\n";
                $message .= "Silakan login ke sistem Smart Box.";

                @file_get_contents(
                    "https://api.telegram.org/bot$token/sendMessage?chat_id=$chatId&text=" . urlencode($message)
                );

            } catch (\Exception $e) {
                // abaikan jika telegram gagal
            }

            return redirect()->back()->with(
                'success',
                'Data penghuni berhasil ditambahkan dan akun dibuat.'
            );

        } catch (\Exception $e) {

            DB::rollBack();

            return redirect()->back()->with(
                'error',
                'Gagal menambahkan penghuni: ' . $e->getMessage()
            );
        }
    }

    public function training($id)
    {
        $penghuni = Penghuni::findOrFail($id);

        $namaFolder = strtolower(str_replace(' ', '_', $penghuni->nama));
        $datasetPath = public_path("dataset/" . $namaFolder);
        
        if (!is_dir($datasetPath)) {

            Activitylog::create([
                'user_id' => auth::id(),
                'activity' => "Training gagal {$penghuni->nama} (dataset tidak ada)",
                'status' => 'failed',
                'tanggal' => now(),
            ]);

            return back()->with('error', 'Folder dataset tidak ditemukan.');
        }

        try {

            // ===============================
            // HITUNG WAKTU MULAI
            // ===============================
            $startTime = microtime(true);

            // PATH PYTHON
            $python = '"C:\\laragon\\bin\\python\\python-3.10\\python.exe"';

            // PATH SCRIPT
             $script = '"C:\\laragon\\www\\smartbox_web\\generate_embeddings.py"';

            // Jalankan Python
            $command = $python . ' ' . $script;
            exec($command, $output, $resultCode);

            // ===============================
            // HITUNG WAKTU SELESAI
            // ===============================
            $endTime = microtime(true);
            $durasi = round($endTime - $startTime, 2);

            if ($resultCode !== 0) {
                return back()->with('error', 'Generate wajah gagal.');
            }

            // Update status
            $penghuni->status_wajah = 'sudah';
            $penghuni->save();

            // Telegram notif
            $user = User::find($penghuni->user_id);

            if ($user && $user->telegram_id) {

                $token = env('TELEGRAM_BOT_TOKEN');
                $chatId = $user->telegram_id;

                $message = "Data wajah Anda berhasil diproses.\n";
                $message .= "Smart Box siap digunakan.";

                file_get_contents(
                    "https://api.telegram.org/bot$token/sendMessage?chat_id=$chatId&text=" . urlencode($message)
                );
            }

            Activitylog::create([
                'user_id' => auth::id(),
                'activity' => "Training wajah berhasil {$penghuni->nama}",
                'status' => 'success',
                'tanggal' => now(),
            ]);

            return back()->with('success', 'Generate wajah berhasil dalam ' . $durasi . ' detik.');

        } catch (\Exception $e) {

            return back()->with('error', $e->getMessage());
        }
    }

    public function hapusPenghuni($id)
    {
        $penghuni = Penghuni::findOrFail($id);
        $nama = $penghuni->nama;

        // 1️⃣ Hapus dataset wajah
        $namaFolder = strtolower(str_replace(' ', '_', $nama));
        $pathDataset = public_path("dataset/" . $namaFolder);
        if (File::exists($pathDataset)) {
            File::deleteDirectory($pathDataset);
        }

        // 2️⃣ Hapus akun user terkait
        if ($penghuni->user_id) {
            User::where('id', $penghuni->user_id)->delete();
        }

        // 3️⃣ Hapus data penghuni
        $penghuni->delete();

        // 4️⃣ Reset status wajah (opsional, sesuai desain kamu)
        //Penghuni::where('status_wajah', 'sudah')
           // ->update(['status_wajah' => 'belum']); 

        // 5️⃣ Log aktivitas
        $user = Auth::user();
        activity(
            "Menghapus penghuni dan akun login: $nama",
            $user->nama ?? 'Admin'
        );

        return back()->with(
            'success',
            'Penghuni dan akun login berhasil dihapus.'
        );
    }

    public function history(Request $request)
    {
        $query = ActivityLog::query();

        // Filter tanggal
        if ($request->filled('tanggal')) {
            $query->whereDate('tanggal', $request->tanggal);
    }

        // Filter pencarian nama atau aktivitas
        if ($request->filled('search')) {
            $search = $request->search;
            $query->where(function($q) use ($search) {
                $q->where('nama', 'like', "%{$search}%")
                  ->orWhere('activity', 'like', "%{$search}%");
            });
    }

        // Urutkan berdasarkan tanggal terbaru
        $logs = $query->orderBy('tanggal', 'desc')->paginate(10);

        return view('admin.history.index', compact('logs'));
    }


}
