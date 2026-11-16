<?php

namespace App\Http\Controllers\penghuni;

use App\Http\Controllers\Controller;
use App\Models\Activitylog;
use App\Models\User;
use App\Models\Paket;
use Illuminate\Support\Facades\Auth;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Hash;

class PenghuniController extends Controller
{
    public function dashboard()
    {
        $user = Auth::user();

        $penghuni = $user->penghuni;

        // Ambil log milik penghuni ini
        $logs = ActivityLog::where('user_id', Auth::id())
                    ->orderBy('created_at', 'desc')
                    ->take(5)
                    ->get();

        return view('penghuni.dashboard.index', compact('logs', 'penghuni'));
    }

    public function uploadWajah(Request $request)
    {
        try {

            // ✅ VALIDASI
            $request->validate([
                'fotos' => 'required|array|size:5',
                'fotos.*' => 'image|mimes:jpg,jpeg,png|max:2048'
            ]);

            // ✅ AMBIL PENGHUNI DARI USER LOGIN
            $penghuni = Auth::user()->penghuni;

            if (!$penghuni) {
                return back()->with('error', 'Data penghuni tidak ditemukan!');
            }

            // ✅ BUAT NAMA FOLDER DARI NAMA PENGHUNI
            $namaFolder = strtolower(str_replace(' ', '_', $penghuni->nama));
            $path = public_path("dataset/$namaFolder");

            if (!file_exists($path)) {
                mkdir($path, 0777, true);
            }

            // ✅ SIMPAN 5 FOTO
            foreach ($request->file('fotos') as $index => $foto) {
                $namaFile = ($index + 1) . ".jpg";
                $foto->move($path, $namaFile);
            }

            // ✅ UPDATE STATUS WAJAH
            $penghuni->update([
                'status_wajah' => 'captured'
            ]);

            return back()->with('success', '✅ Data wajah berhasil diupload!');

        } catch (\Exception $e) {
            return back()->with('error', '❌ Gagal upload: ' . $e->getMessage());
        }
    }

    public function paketIndex()
    {
        $pakets = Paket::where('user_id', Auth::id())
                ->latest()
                ->get();

        return view('penghuni.paket.index', compact('pakets'));
    }

    public function paketCreate()
    {
        return view('penghuni.paket.create');
    }

    public function paketStore(Request $request)
    {
        $request->validate([
            'nomor_resi' => 'required|unique:pakets,nomor_resi',
        ]);

        Paket::create([
            'user_id' => Auth::id(),
            'nomor_resi' => $request->nomor_resi,
            'status' => 'Dalam perjalanan',
        ]);

        activity("Menambahkan nomor resi: " . $request->nomor_resi, "success");

        return redirect()->route('penghuni.paket.index')
            ->with('success', 'Nomor resi berhasil ditambahkan!');
    }

    public function paketDestroy($id)
    {
        $paket = Paket::where('id', $id)
                    ->where('user_id', Auth::id())
                    ->firstOrFail();

        if ($paket->status != 'Dalam perjalanan') {
            return redirect()->route('penghuni.paket.index')
                ->with('error', 'Paket tidak bisa dibatalkan.');
        }

        $paket->update([
            'status' => 'Dibatalkan'
        ]);

        activity("Membatalkan nomor resi: " . $paket->nomor_resi, "success");

        return redirect()->route('penghuni.paket.index')
            ->with('success', 'Nomor resi berhasil dibatalkan!');
    }
    
    public function history(Request $request)
    {
        $query = ActivityLog::where('user_id', Auth::id());

        // Filter tanggal
        if ($request->filled('tanggal')) {
            $query->whereDate('tanggal', $request->tanggal);
        }

        // Filter pencarian
        if ($request->filled('search')) {
            $search = $request->search;
            $query->where(function ($q) use ($search) {
                $q->where('nama', 'like', "%{$search}%")
                  ->orWhere('activity', 'like', "%{$search}%");
            });
        }

        $logs = $query->orderBy('tanggal', 'desc')->paginate(10);

        return view('penghuni.history.index', compact('logs'));
    }
}
