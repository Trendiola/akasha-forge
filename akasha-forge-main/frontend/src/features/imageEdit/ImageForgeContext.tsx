import { createContext, useCallback, useContext, useEffect, type ReactNode } from "react";
import { toast } from "sonner";
import { useForgeItems, useCreateForgeItem, useUpdateForgeItem, type ForgeItem } from "@/features/forge/hooks";

interface ImageForgeCtx {
  projectId?: string | null;
  assets: ForgeItem[];
  galleries: ForgeItem[];
  activeAsset: ForgeItem | null;
  setCanvasAsset: (assetId: string | null) => Promise<void>;
  openOnCanvas: (assetId: string) => Promise<void>;
  addToGallery: (galleryId: string, assetId: string) => Promise<void>;
}

const Ctx = createContext<ImageForgeCtx | null>(null);

export function useImageForge(): ImageForgeCtx {
  const c = useContext(Ctx);
  if (!c) throw new Error("useImageForge must be used within ImageForgeProvider");
  return c;
}

export function ImageForgeProvider({
  projectId,
  onSwitchTab,
  children,
}: {
  projectId?: string | null;
  onSwitchTab: (tab: string) => void;
  children: ReactNode;
}) {
  const assetsQ = useForgeItems(projectId, "image", "asset");
  const { data: galleries = [] } = useForgeItems(projectId, "image", "gallery");
  const canvasQ = useForgeItems(projectId, "image", "canvas_state");
  const create = useCreateForgeItem(projectId ?? "", "image");
  const update = useUpdateForgeItem(projectId ?? "", "image");

  const assets = assetsQ.data ?? [];
  const canvasState = (canvasQ.data ?? [])[0] ?? null;
  const canvasAssetId: string | null = canvasState?.data?.asset_id ?? null;
  const activeAsset = canvasAssetId ? assets.find((a) => a.id === canvasAssetId) ?? null : null;

  // If the persisted canvas asset was deleted, clear the reference safely.
  useEffect(() => {
    if (assetsQ.isSuccess && canvasState && canvasAssetId && !assets.some((a) => a.id === canvasAssetId)) {
      update.mutateAsync({ id: canvasState.id, data: { asset_id: null } }).catch(() => {});
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [assetsQ.isSuccess, canvasAssetId, assets, canvasState?.id]);

  const setCanvasAsset = useCallback(
    async (assetId: string | null) => {
      if (canvasState) await update.mutateAsync({ id: canvasState.id, data: { asset_id: assetId } });
      else await create.mutateAsync({ kind: "canvas_state", title: "canvas", data: { asset_id: assetId } });
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [canvasState?.id]
  );

  const openOnCanvas = useCallback(
    async (assetId: string) => {
      await setCanvasAsset(assetId);
      onSwitchTab("canvas");
    },
    [setCanvasAsset, onSwitchTab]
  );

  const addToGallery = useCallback(
    async (galleryId: string, assetId: string) => {
      const g = galleries.find((x) => x.id === galleryId);
      if (!g) return;
      const members: string[] = Array.isArray(g.data?.asset_ids) ? g.data.asset_ids : [];
      if (members.includes(assetId)) {
        toast.info("Already in this gallery");
        return;
      }
      await update.mutateAsync({ id: galleryId, data: { ...g.data, asset_ids: [...members, assetId] } });
      toast.success(`Added to “${g.title}”`);
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [galleries]
  );

  return (
    <Ctx.Provider value={{ projectId, assets, galleries, activeAsset, setCanvasAsset, openOnCanvas, addToGallery }}>
      {children}
    </Ctx.Provider>
  );
}
