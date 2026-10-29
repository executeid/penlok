@extends('layouts.admin')

@section('content')
<div class="container mt-4">
    <h3 class="mb-3">Monitoring Training Wajah</h3>

    <div class="card p-4">
        <p><strong>Status:</strong> <span id="statusText">Memuat...</span></p>

        <div class="progress mb-3" style="height: 30px;">
            <div id="progressBar" 
                 class="progress-bar bg-success" 
                 role="progressbar" 
                 style="width: 0%">0%
            </div>
        </div>

        <p class="text-muted">Halaman ini akan update otomatis setiap 1 detik.</p>
    </div>
</div>

<script>
function loadProgress() {
    fetch('/progress-training')
        .then(res => res.json())
        .then(data => {
            let progress = data.progress;
            let status = data.status;

            document.getElementById("progressBar").style.width = progress + "%";
            document.getElementById("progressBar").innerHTML = progress + "%";
            document.getElementById("statusText").innerHTML = status;

            if (progress >= 100) {
                Swal.fire({
                    icon: 'success',
                    title: 'Training selesai!',
                    text: 'Model wajah berhasil dilatih.',
                    timer: 3500,
                    showConfirmButton: false
                });
            }
        });
}

setInterval(loadProgress, 1000);
loadProgress();
</script>
@endsection
