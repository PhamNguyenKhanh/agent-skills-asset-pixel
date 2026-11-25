using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.Animations;
using UnityEditor.U2D.Sprites;
using UnityEngine;

namespace PixelForge.Unity
{
    /// <summary>
    /// Pixel Forge Unity 6 Auto-Importer.
    /// Configures pixel-perfect Sprite texture import settings (FilterMode.Point, Uncompressed, no mipmaps),
    /// slices sprite sheets using ISpriteEditorDataProvider with mandatory ISpriteFrameEditCapability checks,
    /// assigns exact pixel-aligned pivots (SpriteAlignment.Custom), and generates AnimationClips,
    /// AnimatorControllers, and ready-to-drop Prefabs.
    /// </summary>
    public static class PixelForgeImporter
    {
        private const string MenuPath = "Assets/Pixel Forge/Import Bundle";

#pragma warning disable CS0649
        [Serializable]
        private sealed class JobDescriptor
        {
            public int version;
            public string assetId;
            public int pixelsPerUnit;
            public TextureSpec texture;
            public ClipSpec[] clips;
        }

        [Serializable]
        private sealed class TextureSpec
        {
            public string relativePath;
            public int width;
            public int height;
            public SliceSpec[] slices;
        }

        [Serializable]
        private sealed class SliceSpec
        {
            public string name;
            public string guid;
            public int x;
            public int y;
            public int width;
            public int height;
            public float pivotX;
            public float pivotY;
        }

        [Serializable]
        private sealed class ClipSpec
        {
            public string name;
            public string playback;
            public int fps;
            public FrameKey[] frames;
        }

        [Serializable]
        private sealed class FrameKey
        {
            public string sliceName;
            public int startMs;
            public int durationMs;
            public string eventName;
        }
#pragma warning restore CS0649

        [MenuItem(MenuPath, true)]
        private static bool CanImportSelected()
        {
            if (!(Selection.activeObject is TextAsset asset))
                return false;
            var path = AssetDatabase.GetAssetPath(asset);
            return path.EndsWith("PixelForge.job.json", StringComparison.OrdinalIgnoreCase);
        }

        [MenuItem(MenuPath)]
        private static void ImportSelected()
        {
            if (!CanImportSelected())
            {
                throw new InvalidOperationException("Select a PixelForge.job.json file in the Project window.");
            }

            var jobAsset = (TextAsset)Selection.activeObject;
            var jobPath = AssetDatabase.GetAssetPath(jobAsset);
            var bundleDir = Path.GetDirectoryName(jobPath).Replace('\\', '/');
            var job = JsonUtility.FromJson<JobDescriptor>(jobAsset.text);
            if (job == null || job.version != 1 || job.pixelsPerUnit <= 0 || job.texture == null)
            {
                throw new InvalidDataException("Invalid or unsupported PixelForge.job.json descriptor.");
            }

            var generatedDir = bundleDir + "/Generated";
            if (!AssetDatabase.IsValidFolder(generatedDir))
            {
                AssetDatabase.CreateFolder(bundleDir, "Generated");
            }

            var sprites = ImportAndSliceTexture(bundleDir, job);
            var clips = CreateAnimationClips(generatedDir, job, sprites);
            CreateControllerAndPrefab(generatedDir, job, sprites, clips);

            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();
            var folderObj = AssetDatabase.LoadAssetAtPath<DefaultAsset>(generatedDir);
            Selection.activeObject = folderObj;
            EditorGUIUtility.PingObject(folderObj);
            Debug.Log($"[PixelForge] Imported '{job.assetId}' ({sprites.Count} sprites, {clips.Count} clips) into {generatedDir}.");
        }

        private static Dictionary<string, Sprite> ImportAndSliceTexture(string bundleDir, JobDescriptor job)
        {
            var texPath = bundleDir + "/" + job.texture.relativePath.Replace('\\', '/');
            var importer = AssetImporter.GetAtPath(texPath) as TextureImporter;
            if (importer == null)
            {
                throw new IOException($"[PixelForge] Missing texture at {texPath}.");
            }

            // Pixel-Perfect 2D texture settings (configure-2d-pixel-perfect standard)
            importer.textureType = TextureImporterType.Sprite;
            importer.spriteImportMode = SpriteImportMode.Multiple;
            importer.spritePixelsPerUnit = job.pixelsPerUnit;
            importer.filterMode = FilterMode.Point;
            importer.wrapMode = TextureWrapMode.Clamp;
            importer.mipmapEnabled = false;
            importer.textureCompression = TextureImporterCompression.Uncompressed;
            importer.crunchedCompression = false;
            importer.npotScale = TextureImporterNPOTScale.None;
            importer.alphaSource = TextureImporterAlphaSource.FromInput;
            importer.alphaIsTransparency = true;
            importer.maxTextureSize = Mathf.Max(32, Mathf.NextPowerOfTwo(Mathf.Max(job.texture.width, job.texture.height)));

            var settings = new TextureImporterSettings();
            importer.ReadTextureSettings(settings);
            settings.spriteMeshType = SpriteMeshType.FullRect;
            settings.spriteGenerateFallbackPhysicsShape = false;
            importer.SetTextureSettings(settings);

            // Safe Core Pattern: ISpriteEditorDataProvider + mandatory ISpriteFrameEditCapability checks
            var factory = new SpriteDataProviderFactories();
            factory.Init();
            var dataProvider = factory.GetSpriteEditorDataProviderFromObject(importer);
            dataProvider.InitSpriteEditorDataProvider();

            var editCapability = dataProvider.GetDataProvider<ISpriteFrameEditCapability>();
            if (editCapability == null)
            {
                throw new InvalidOperationException("[PixelForge] Importer does not expose ISpriteFrameEditCapability. Operation aborted safely.");
            }

            var caps = editCapability.GetEditCapability();
            if (!caps.HasCapability(EEditCapability.CreateAndDeleteSprite)
                || !caps.HasCapability(EEditCapability.EditSpriteName)
                || !caps.HasCapability(EEditCapability.EditSpriteRect)
                || !caps.HasCapability(EEditCapability.EditPivot))
            {
                throw new InvalidOperationException("[PixelForge] Required Sprite edit capabilities missing on importer. Operation aborted safely.");
            }

            var spriteRects = job.texture.slices.Select(s => new SpriteRect
            {
                name = s.name,
                spriteID = new GUID(s.guid),
                rect = new Rect(s.x, s.y, s.width, s.height),
                alignment = SpriteAlignment.Custom,
                pivot = new Vector2(s.pivotX / Mathf.Max(1, s.width), s.pivotY / Mathf.Max(1, s.height)),
            }).ToArray();

            dataProvider.SetSpriteRects(spriteRects);
            var nameFileId = dataProvider.GetDataProvider<ISpriteNameFileIdDataProvider>();
            if (nameFileId != null)
            {
                nameFileId.SetNameFileIdPairs(spriteRects.Select(sr => new SpriteNameFileIdPair(sr.name, sr.spriteID)).ToArray());
            }

            dataProvider.Apply();
            importer.SaveAndReimport();

            var loaded = AssetDatabase.LoadAllAssetsAtPath(texPath).OfType<Sprite>().ToDictionary(s => s.name, s => s);
            if (loaded.Count != job.texture.slices.Length)
            {
                throw new InvalidDataException($"[PixelForge] Expected {job.texture.slices.Length} sliced sprites, found {loaded.Count}.");
            }
            return loaded;
        }

        private static List<AnimationClip> CreateAnimationClips(
            string generatedDir,
            JobDescriptor job,
            Dictionary<string, Sprite> sprites)
        {
            var created = new List<AnimationClip>();
            if (job.clips == null) return created;

            foreach (var clipSpec in job.clips)
            {
                if (clipSpec.frames == null || clipSpec.frames.Length == 0) continue;

                var clip = new AnimationClip
                {
                    name = $"{job.assetId}_{clipSpec.name}",
                    frameRate = Mathf.Max(1, clipSpec.fps),
                };

                var loop = !string.Equals(clipSpec.playback, "once", StringComparison.OrdinalIgnoreCase);
                var clipSettings = AnimationUtility.GetAnimationClipSettings(clip);
                clipSettings.loopTime = loop;
                AnimationUtility.SetAnimationClipSettings(clip, clipSettings);

                var binding = EditorCurveBinding.PPtrCurve(string.Empty, typeof(SpriteRenderer), "m_Sprite");
                var keys = new ObjectReferenceKeyframe[clipSpec.frames.Length + 1];
                var events = new List<AnimationEvent>();
                int totalMs = 0;

                for (int i = 0; i < clipSpec.frames.Length; i++)
                {
                    var fk = clipSpec.frames[i];
                    keys[i] = new ObjectReferenceKeyframe
                    {
                        time = fk.startMs / 1000f,
                        value = sprites[fk.sliceName],
                    };
                    totalMs = fk.startMs + fk.durationMs;
                    if (!string.IsNullOrEmpty(fk.eventName))
                    {
                        events.Add(new AnimationEvent { time = fk.startMs / 1000f, functionName = "OnPixelForgeEvent", stringParameter = fk.eventName });
                    }
                }

                // Terminal key preserves final frame's full duration.
                var lastRef = loop ? clipSpec.frames[0].sliceName : clipSpec.frames[clipSpec.frames.Length - 1].sliceName;
                keys[clipSpec.frames.Length] = new ObjectReferenceKeyframe
                {
                    time = totalMs / 1000f,
                    value = sprites[lastRef],
                };

                AnimationUtility.SetObjectReferenceCurve(clip, binding, keys);
                if (events.Count > 0)
                {
                    AnimationUtility.SetAnimationEvents(clip, events.ToArray());
                }

                var clipPath = $"{generatedDir}/{clip.name}.anim";
                AssetDatabase.CreateAsset(clip, clipPath);
                created.Add(clip);
            }

            return created;
        }

        private static void CreateControllerAndPrefab(
            string generatedDir,
            JobDescriptor job,
            Dictionary<string, Sprite> sprites,
            List<AnimationClip> clips)
        {
            AnimatorController controller = null;
            if (clips.Count > 0)
            {
                var ctrlPath = $"{generatedDir}/{job.assetId}.controller";
                controller = AnimatorController.CreateAnimatorControllerAtPath(ctrlPath);
                var sm = controller.layers[0].stateMachine;
                for (int i = 0; i < clips.Count; i++)
                {
                    var state = sm.AddState(clips[i].name);
                    state.motion = clips[i];
                    if (i == 0) sm.defaultState = state;
                }
            }

            var firstSprite = sprites[job.texture.slices[0].name];
            var go = new GameObject(job.assetId);
            try
            {
                var renderer = go.AddComponent<SpriteRenderer>();
                renderer.sprite = firstSprite;
                if (controller != null)
                {
                    var animator = go.AddComponent<Animator>();
                    animator.runtimeAnimatorController = controller;
                }
                var prefabPath = $"{generatedDir}/{job.assetId}.prefab";
                PrefabUtility.SaveAsPrefabAsset(go, prefabPath);
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(go);
            }
        }
    }
}
