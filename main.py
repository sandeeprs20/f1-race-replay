import fastf1
import os


def main():
    cache_dir = ".fastf1-cache"
    os.makedirs(cache_dir, exist_ok=True)
    fastf1.Cache.enable_cache(cache_dir)
    print(f"Setup OK: FastF1 cache enabled at {cache_dir}")


if __name__ == "__main__":
    main()
