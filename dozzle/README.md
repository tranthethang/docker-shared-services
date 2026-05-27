# Dozzle authentication (simple / users.yml)

Mặc định Dozzle được cấu hình với `--auth-provider=simple`, đọc user từ file:

`dozzle/users.yml`

## Tài khoản mặc định

- Username: `admin`
- Password (plaintext): `password102`

Dozzle lưu password dưới dạng **bcrypt hash** trong file `users.yml`.

## Tạo `dozzle/users.yml` thủ công

Chạy lệnh sau (nó sẽ tự generate bcrypt hash và ghi vào `dozzle/users.yml`):

```bash
docker run --rm -i amir20/dozzle generate admin \
  --password password102 \
  --email admin@example.com \
  --name "Admin" > ./dozzle/users.yml
```

## Khi chạy `make setup`

`make setup` sẽ tự kiểm tra và tạo `dozzle/users.yml` nếu file chưa tồn tại.
