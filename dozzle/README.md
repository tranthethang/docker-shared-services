# Dozzle authentication (simple / users.yml)

Mặc định Dozzle được cấu hình với `--auth-provider=simple`, đọc user từ file:

`dozzle/data/users.yml`

## Tài khoản mặc định

- Username: `admin`
- Password (plaintext): `password102`

Dozzle lưu password dưới dạng **bcrypt hash** trong file `users.yml`.

## Tạo `dozzle/data/users.yml` thủ công

Chạy lệnh sau (nó sẽ tự generate bcrypt hash và ghi vào `dozzle/data/users.yml`):

```bash
docker run --rm -i amir20/dozzle generate admin \
  --password password102 \
  --email admin@example.com \
  --name "Admin" > ./dozzle/data/users.yml
```

## Khi chạy `make setup`

`make setup` sẽ tự kiểm tra và tạo `dozzle/data/users.yml` nếu file chưa tồn tại.

## Chạy từ root repo (`make up`)

`make up` chạy `docker compose` từ thư mục gốc repo, nên volume dùng `${PWD}/dozzle/data:/data` (không dùng `./data`, vì sẽ mount nhầm thư mục `data/` ở root).

Nếu container đã tạo trước đó với mount cũ, recreate:

```bash
make up service=dozzle
# hoặc
docker compose -f docker-compose.shared.yml -f dozzle/docker-compose.yml up -d --force-recreate
```
